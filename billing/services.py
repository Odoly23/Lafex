from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from config.models import SystemSetting

from .models import Entitlement, Plan, UsageDay, Voucher


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
def redeem(user, raw_code):
	"""Voucher sekali pakai. Jika paket masih aktif, waktunya ditambahkan di belakangnya."""
	code = (raw_code or '').strip().upper()
	v = Voucher.objects.select_for_update().select_related('plan').filter(code=code).first()
	if not v:
		raise VoucherError('voucher_unknown')
	if v.used_by_id:
		raise VoucherError('voucher_used')
	ent = Entitlement.objects.select_for_update().filter(user=user).first()
	now = timezone.now()
	base = max(now, ent.expires_at) if ent else now
	new_exp = base + timedelta(hours=v.plan.hours)
	if ent:
		ent.expires_at = new_exp
		ent.save(update_fields=['expires_at'])
	else:
		Entitlement.objects.create(user=user, expires_at=new_exp)
	v.used_by, v.used_at = user, now
	v.save(update_fields=['used_by', 'used_at'])
	return new_exp


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


def create_vouchers(plan_code, count):
	import secrets
	plan = Plan.objects.get(code=plan_code)
	out = []
	for _ in range(count):
		code = '-'.join(secrets.token_hex(2).upper() for _ in range(3))
		out.append(Voucher.objects.create(code=code, plan=plan).code)
	return out
