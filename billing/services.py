from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from config.models import SystemSetting

from . import vouchers
from .models import Entitlement, Plan, RedeemAttempt, UsageDay, Voucher, VoucherBatch


class VoucherError(Exception):
	def __init__(self, code):
		super().__init__(code)
		self.code = code


def expires_at(user):
	ent = Entitlement.objects.filter(user=user).first()
	return ent.expires_at if ent else None


def is_active(user):
	exp = expires_at(user)
	return bool(exp and exp > timezone.now())


@transaction.atomic
def grant_plan(user, plan):
	"""Tambah masa aktif sesuai paket (di belakang masa aktif yang masih berjalan). Dipakai voucher dan admin."""
	ent = Entitlement.objects.select_for_update().filter(user=user).first()
	now = timezone.now()
	base = max(now, ent.expires_at) if ent else now
	new_exp = base + timedelta(hours=plan.hours)
	if ent:
		ent.expires_at = new_exp
		ent.save(update_fields=['expires_at'])
	else:
		Entitlement.objects.create(user=user, expires_at=new_exp)
	return new_exp


# ---- Voucher (gaya pulsa/token) ----
ATTEMPT_WINDOW = timedelta(minutes=15)
MAX_USER_FAILS = 5     # salah memasukkan kode per siswa per 15 menit
MAX_IP_FAILS = 30      # per IP (lebih longgar: satu wifi sekolah dipakai banyak siswa)


def _check_rate_limit(user, ip):
	since = timezone.now() - ATTEMPT_WINDOW
	fails = RedeemAttempt.objects.filter(ok=False, created_at__gte=since)
	if fails.filter(user=user).count() >= MAX_USER_FAILS or (ip and fails.filter(ip=ip).count() >= MAX_IP_FAILS):
		raise VoucherError('rate_limited')


@transaction.atomic
def _redeem_locked(user, raw_code):
	if not vouchers.looks_valid(raw_code):
		raise VoucherError('voucher_unknown')
	v = (Voucher.objects.select_for_update().select_related('plan', 'batch')
         .filter(code_hash=vouchers.hash_code(raw_code)).first())
	if not v:
		raise VoucherError('voucher_unknown')
	status = v.status
	if status != 'available':
		raise VoucherError({'used': 'voucher_used', 'void': 'voucher_void', 'expired': 'voucher_expired'}[status])
	new_exp = grant_plan(user, v.plan)
	v.used_by, v.used_at = user, timezone.now()
	v.save(update_fields=['used_by', 'used_at'])
	return new_exp


def redeem(user, raw_code, ip=''):
	"""Pakai voucher sekali pakai. Jika paket masih aktif, waktunya ditambahkan di belakangnya.
    Percobaan salah dibatasi agar kode tidak bisa ditebak."""
	_check_rate_limit(user, ip)
	try:
		new_exp = _redeem_locked(user, raw_code)
	except VoucherError:
		RedeemAttempt.objects.create(user=user, ip=ip or '', ok=False)
		raise
	RedeemAttempt.objects.create(user=user, ip=ip or '', ok=True)
	return new_exp


@transaction.atomic
def create_batch(plan, count, label, created_by=None, valid_days=365):
	"""Buat satu batch voucher. Mengembalikan (batch, [(serial, kode_rahasia), ...]).
    Kode rahasia hanya ada di nilai kembalian ini (tampilkan/cetak sekarang); database hanya menyimpan hash-nya."""
	batch = VoucherBatch.objects.create(
        label=label[:80], plan=plan, quantity=count, created_by=created_by,
        valid_until=timezone.now() + timedelta(days=valid_days))
	rows, objs, seen = [], [], set()
	for i in range(1, count + 1):
		while True:
			code = vouchers.generate_code()
			h = vouchers.hash_code(code)
			if h not in seen:
				seen.add(h)
				break
		serial = f'LFX-{batch.pk:04d}-{i:04d}'
		objs.append(Voucher(serial=serial, code_hash=h, batch=batch, plan=plan))
		rows.append((serial, code))
	Voucher.objects.bulk_create(objs)
	return batch, rows


def create_vouchers(plan_code, count, label='CLI'):
	"""Pembantu sederhana: kembalikan daftar kode rahasia (untuk perintah CLI dan tes)."""
	plan = Plan.objects.get(code=plan_code)
	_, rows = create_batch(plan, count, label)
	return [code for _, code in rows]


@transaction.atomic
def void_batch(batch):
	"""Batalkan batch: voucher yang belum dipakai tidak valid lagi. Yang sudah dipakai tidak terpengaruh."""
	if batch.voided_at is None:
		batch.voided_at = timezone.now()
		batch.save(update_fields=['voided_at'])


def void_voucher(voucher):
	if voucher.status == 'available':
		voucher.voided_at = timezone.now()
		voucher.save(update_fields=['voided_at'])
		return True
	return False


def has_access(user):
	"""Akses penuh: paket aktif, atau sistem sedang dalam mode gratis (admin mematikan 'presiza pakote')."""
	return (not SystemSetting.load().payments_required) or is_active(user)


def daily_limit(user):
	s = SystemSetting.load()
	return s.paid_turns_per_day if has_access(user) else s.free_turns_per_day


def turns_left(user):
	used = UsageDay.objects.filter(user=user, day=timezone.localdate()).values_list('turns', flat=True).first() or 0
	return max(0, daily_limit(user) - used)


def consume_turn(user):
	"""Ambil satu jatah secara atomik. False bila habis."""
	day, limit = timezone.localdate(), daily_limit(user)
	try:
		UsageDay.objects.get_or_create(user=user, day=day)
	except IntegrityError:  # balapan dua permintaan: baris sudah dibuat yang lain
		pass
	return UsageDay.objects.filter(user=user, day=day, turns__lt=limit).update(turns=F('turns') + 1) == 1


def refund_turn(user):
	UsageDay.objects.filter(user=user, day=timezone.localdate(), turns__gt=0).update(turns=F('turns') - 1)
