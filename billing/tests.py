from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from users.models import User

from . import services, vouchers
from .models import Plan, UsageDay, Voucher


def post(client, url, data):
	return client.post(url, data, content_type='application/json')


class PlanSeedTests(TestCase):
	def test_default_plans_are_cheaper_per_day_as_they_get_longer(self):
		plans = list(Plan.objects.order_by('hours'))
		self.assertEqual([p.code for p in plans], ['1d', '3d', '7d', '30d', '365d'])
		per_day = [float(p.price_usd) / (p.hours / 24) for p in plans]
		self.assertEqual(per_day, sorted(per_day, reverse=True), 'paket lebih panjang harus lebih murah per hari')


class VoucherTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('a@x.com')

	def test_redeem_activates_access(self):
		code, = services.create_vouchers('1d', 1)
		self.assertFalse(services.is_active(self.user))
		exp = services.redeem(self.user, code)
		self.assertTrue(services.is_active(self.user))
		self.assertAlmostEqual((exp - timezone.now()).total_seconds(), 24 * 3600, delta=5)

	def test_voucher_is_single_use_and_case_insensitive(self):
		code, = services.create_vouchers('1d', 1)
		services.redeem(self.user, code.lower())
		other = User.objects.create_user('b@x.com')
		with self.assertRaises(services.VoucherError) as cm:
			services.redeem(other, code)
		self.assertEqual(cm.exception.code, 'voucher_used')
		self.assertFalse(services.is_active(other))

	def test_unknown_voucher(self):
		with self.assertRaises(services.VoucherError) as cm:
			services.redeem(self.user, 'NOPE')
		self.assertEqual(cm.exception.code, 'voucher_unknown')

	def test_vouchers_stack_on_active_plan(self):
		a, b = services.create_vouchers('7d', 2)
		first = services.redeem(self.user, a)
		second = services.redeem(self.user, b)
		self.assertEqual(second - first, timedelta(days=7))

	def test_expired_plan_restarts_from_now(self):
		from .models import Entitlement
		Entitlement.objects.create(user=self.user, expires_at=timezone.now() - timedelta(days=3))
		code, = services.create_vouchers('1d', 1)
		exp = services.redeem(self.user, code)
		self.assertAlmostEqual((exp - timezone.now()).total_seconds(), 24 * 3600, delta=5)


class QuotaTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('a@x.com')

	@override_settings(FREE_TURNS_PER_DAY=2, PAID_TURNS_PER_DAY=4)
	def test_free_then_paid_limits(self):
		self.assertTrue(services.consume_turn(self.user))
		self.assertTrue(services.consume_turn(self.user))
		self.assertFalse(services.consume_turn(self.user))
		self.assertEqual(services.turns_left(self.user), 0)
		services.redeem(self.user, services.create_vouchers('1d', 1)[0])
		self.assertEqual(services.turns_left(self.user), 2)  # batas berbayar 4, sudah dipakai 2
		self.assertTrue(services.consume_turn(self.user))
		self.assertTrue(services.consume_turn(self.user))
		self.assertFalse(services.consume_turn(self.user))

	@override_settings(FREE_TURNS_PER_DAY=1)
	def test_refund_and_new_day_reset(self):
		self.assertTrue(services.consume_turn(self.user))
		services.refund_turn(self.user)
		self.assertTrue(services.consume_turn(self.user))
		self.assertFalse(services.consume_turn(self.user))
		UsageDay.objects.update(day=timezone.localdate() - timedelta(days=1))
		self.assertTrue(services.consume_turn(self.user))

	def test_refund_never_goes_negative(self):
		services.refund_turn(self.user)
		self.assertEqual(UsageDay.objects.count(), 0)


class BillingApiTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('a@x.com')

	def test_requires_login(self):
		self.assertEqual(self.client.get('/api/me/').status_code, 401)
		self.assertEqual(post(self.client, '/api/redeem/', {'code': 'X'}).status_code, 401)

	def test_me_and_redeem(self):
		self.client.force_login(self.user)
		me = self.client.get('/api/me/').json()
		self.assertFalse(me['active'])
		self.assertEqual(me['band'], 'beginner')
		self.assertEqual(len(me['plans']), 5)
		code, = services.create_vouchers('30d', 1)
		r = post(self.client, '/api/redeem/', {'code': code})
		self.assertEqual(r.status_code, 200)
		self.assertTrue(r.json()['active'])
		self.assertEqual(post(self.client, '/api/redeem/', {'code': code}).json()['error'], 'voucher_used')
		self.assertEqual(Voucher.objects.get(code_hash=vouchers.hash_code(code)).used_by, self.user)

	def test_create_vouchers_command(self):
		from io import StringIO
		from django.core.management import call_command
		out = StringIO()
		call_command('create_vouchers', '1d', '3', stdout=out)
		self.assertEqual(len(out.getvalue().strip().splitlines()), 3, 'satu baris per voucher: seri + kode')


import re
from datetime import timedelta as _td
from unittest import mock

from django.test import Client
from django.utils import timezone as _tz

from .models import RedeemAttempt, VoucherBatch


class VoucherCodeTests(TestCase):
	def test_format_alphabet_and_uniqueness(self):
		codes = {vouchers.generate_code() for _ in range(2000)}
		self.assertEqual(len(codes), 2000)
		for c in list(codes)[:200]:
			self.assertRegex(c, r'^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$')

	def test_normalization_is_forgiving_but_not_loose(self):
		self.assertEqual(vouchers.normalize(' ab12-cdef-0o1l '), 'AB12CDEF0011')
		self.assertEqual(vouchers.hash_code('ABCD-EFGH-JKMN'), vouchers.hash_code('abcd efgh jkmn'))
		self.assertNotEqual(vouchers.hash_code('ABCD-EFGH-JKMN'), vouchers.hash_code('ABCD-EFGH-JKMP'))
		self.assertTrue(vouchers.looks_valid('abcd-efgh-jkmn'))
		for bad in ('', None, 'ABCD', 'ABCD-EFGH-JKMN-X', 'ABCD-EFGH-JKM!', 'UUUU-UUUU-UUUU'):
			self.assertFalse(vouchers.looks_valid(bad), bad)

	def test_hash_depends_on_pepper(self):
		from django.test import override_settings
		with override_settings(VOUCHER_PEPPER='a'):
			h1 = vouchers.hash_code('ABCD-EFGH-JKMN')
		with override_settings(VOUCHER_PEPPER='b'):
			h2 = vouchers.hash_code('ABCD-EFGH-JKMN')
		self.assertNotEqual(h1, h2)


class VoucherSecurityTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('a@x.com')
		self.plan = Plan.objects.get(code='7d')

	def test_plain_code_is_never_stored(self):
		batch, rows = services.create_batch(self.plan, 5, 'Toko A')
		stored = ' '.join(str(v) for v in Voucher.objects.values_list('serial', 'code_hash'))
		for serial, code in rows:
			self.assertNotIn(code, stored)
			self.assertNotIn(vouchers.normalize(code), stored)
		self.assertFalse(hasattr(Voucher, 'code'), 'tidak ada kolom kode polos')
		self.assertTrue(all(re.fullmatch(r'[0-9a-f]{64}', h) for h in Voucher.objects.values_list('code_hash', flat=True)))

	def test_batch_serials_and_expiry(self):
		batch, rows = services.create_batch(self.plan, 3, 'Toko A', valid_days=30)
		self.assertEqual([s for s, _ in rows], [f'LFX-{batch.pk:04d}-000{i}' for i in (1, 2, 3)])
		self.assertAlmostEqual((batch.valid_until - _tz.now()).days, 29, delta=1)
		self.assertEqual(batch.vouchers.count(), 3)

	def test_each_code_redeems_exactly_once_for_exactly_one_user(self):
		_, rows = services.create_batch(self.plan, 1, 'Toko A')
		code = rows[0][1]
		other = User.objects.create_user('b@x.com')
		services.redeem(self.user, code)
		for u in (self.user, other):
			with self.assertRaises(services.VoucherError) as cm:
				services.redeem(u, code)
			self.assertEqual(cm.exception.code, 'voucher_used')
		self.assertFalse(services.is_active(other))

	def test_typos_that_normalize_still_work(self):
		_, rows = services.create_batch(self.plan, 1, 'Toko A')
		sloppy = rows[0][1].lower().replace('-', ' ')
		services.redeem(self.user, sloppy)
		self.assertTrue(services.is_active(self.user))

	def test_voided_batch_and_single_voucher(self):
		batch, rows = services.create_batch(self.plan, 3, 'Toko A')
		services.void_batch(batch)
		with self.assertRaises(services.VoucherError) as cm:
			services.redeem(self.user, rows[0][1])
		self.assertEqual(cm.exception.code, 'voucher_void')
		batch2, rows2 = services.create_batch(self.plan, 2, 'Toko B')
		v = Voucher.objects.get(serial=rows2[0][0])
		self.assertTrue(services.void_voucher(v))
		with self.assertRaises(services.VoucherError) as cm:
			services.redeem(self.user, rows2[0][1])
		self.assertEqual(cm.exception.code, 'voucher_void')
		services.redeem(self.user, rows2[1][1])  # yang lain di batch yang sama tetap berlaku
		self.assertTrue(services.is_active(self.user))

	def test_void_does_not_affect_vouchers_already_used(self):
		batch, rows = services.create_batch(self.plan, 2, 'Toko A')
		services.redeem(self.user, rows[0][1])
		services.void_batch(batch)
		self.assertTrue(services.is_active(self.user), 'paket yang sudah dipakai tetap berlaku')
		used = Voucher.objects.get(serial=rows[0][0])
		self.assertEqual(used.status, 'used')
		self.assertFalse(services.void_voucher(used), 'voucher terpakai tidak bisa dikansela')

	def test_expired_batch_is_rejected(self):
		batch, rows = services.create_batch(self.plan, 1, 'Toko A')
		VoucherBatch.objects.filter(pk=batch.pk).update(valid_until=_tz.now() - _td(seconds=1))
		with self.assertRaises(services.VoucherError) as cm:
			services.redeem(self.user, rows[0][1])
		self.assertEqual(cm.exception.code, 'voucher_expired')
		self.assertEqual(Voucher.objects.get().status, 'expired')

	def test_available_queryset_excludes_used_void_expired(self):
		b1, r1 = services.create_batch(self.plan, 2, 'A')
		b2, r2 = services.create_batch(self.plan, 1, 'B')
		b3, r3 = services.create_batch(self.plan, 1, 'C')
		services.redeem(self.user, r1[0][1])
		services.void_batch(b2)
		VoucherBatch.objects.filter(pk=b3.pk).update(valid_until=_tz.now() - _td(days=1))
		self.assertEqual(Voucher.objects.available().count(), 1)

	def test_wrong_codes_are_rate_limited_per_user(self):
		_, rows = services.create_batch(self.plan, 1, 'Toko A')
		for _ in range(services.MAX_USER_FAILS):
			with self.assertRaises(services.VoucherError) as cm:
				services.redeem(self.user, 'AAAA-AAAA-AAAA')
			self.assertEqual(cm.exception.code, 'voucher_unknown')
		with self.assertRaises(services.VoucherError) as cm:
			services.redeem(self.user, rows[0][1])  # kode benar pun ditolak sementara
		self.assertEqual(cm.exception.code, 'rate_limited')
		self.assertFalse(Voucher.objects.get().used_by_id)
		other = User.objects.create_user('b@x.com')
		services.redeem(other, rows[0][1])  # siswa lain tidak terkena

	def test_rate_limit_window_expires_and_success_is_not_a_failure(self):
		_, rows = services.create_batch(self.plan, 2, 'Toko A')
		for _ in range(services.MAX_USER_FAILS):
			with self.assertRaises(services.VoucherError):
				services.redeem(self.user, 'AAAA-AAAA-AAAA')
		RedeemAttempt.objects.update(created_at=_tz.now() - _td(minutes=16))
		services.redeem(self.user, rows[0][1])
		services.redeem(self.user, rows[1][1])
		self.assertEqual(RedeemAttempt.objects.filter(ok=True).count(), 2)

	def test_ip_rate_limit_spans_users(self):
		_, rows = services.create_batch(self.plan, 1, 'Toko A')
		for i in range(services.MAX_IP_FAILS):
			RedeemAttempt.objects.create(user=User.objects.create_user(f'u{i}@x.com'), ip='10.0.0.9', ok=False)
		with self.assertRaises(services.VoucherError) as cm:
			services.redeem(self.user, rows[0][1], ip='10.0.0.9')
		self.assertEqual(cm.exception.code, 'rate_limited')
		services.redeem(self.user, rows[0][1], ip='10.0.0.10')

	def test_legacy_migration_hashes_codes_and_assigns_serials(self):
		import importlib
		mig = importlib.import_module('billing.migrations.0003_voucher_batches_hashed_codes')
		saved = []

		class Row:
			def __init__(self, pk, code):
				self.pk, self.code = pk, code
			def save(self, update_fields):
				saved.append((self.pk, self.code_hash, self.serial, update_fields))

		class FakeModel:
			objects = mock.Mock(all=lambda: [Row(7, 'ABCD-EFGH-JKMN')])

		apps = mock.Mock(get_model=lambda app, name: FakeModel)
		mig.hash_existing_codes(apps, None)
		pk, h, serial, fields = saved[0]
		self.assertEqual((pk, serial, h), (7, 'LEG-000007', vouchers.hash_code('abcd efgh jkmn')))
		self.assertEqual(fields, ['code_hash', 'serial'])


class RedeemApiSecurityTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)
		self.plan = Plan.objects.get(code='7d')

	def test_error_codes(self):
		batch, rows = services.create_batch(self.plan, 2, 'Toko A')
		services.void_voucher(Voucher.objects.get(serial=rows[1][0]))
		self.assertEqual(post(self.client, '/api/redeem/', {'code': rows[1][1]}).json()['error'], 'voucher_void')
		self.assertEqual(post(self.client, '/api/redeem/', {'code': rows[0][1]}).status_code, 200)
		self.assertEqual(post(self.client, '/api/redeem/', {'code': rows[0][1]}).json()['error'], 'voucher_used')

	def test_malformed_codes_are_rejected_and_count_as_failed_attempts(self):
		for bad in (None, 123, {}):
			self.assertEqual(post(self.client, '/api/redeem/', {'code': bad}).status_code, 400, bad)
		other = User.objects.create_user('b@x.com')
		self.client.force_login(other)
		self.assertEqual(post(self.client, '/api/redeem/', {'code': 'x' * 5000}).status_code, 400)
		self.assertEqual(RedeemAttempt.objects.filter(ok=False).count(), 4)

	def test_api_rate_limit_is_429(self):
		for _ in range(services.MAX_USER_FAILS):
			post(self.client, '/api/redeem/', {'code': 'AAAA-AAAA-AAAA'})
		r = post(self.client, '/api/redeem/', {'code': 'AAAA-AAAA-AAAA'})
		self.assertEqual((r.status_code, r.json()['error']), (429, 'rate_limited'))

	def test_command_prints_serial_and_code_only_once(self):
		from io import StringIO
		from django.core.management import call_command
		out = StringIO()
		call_command('create_vouchers', '1d', '2', 'Toko Maria', stdout=out, stderr=StringIO())
		lines = [l.split('\t') for l in out.getvalue().strip().splitlines()]
		self.assertEqual(len(lines), 2)
		self.assertRegex(lines[0][0], r'^LFX-\d{4}-0001$')
		self.assertTrue(vouchers.looks_valid(lines[0][1]))
		self.assertEqual(VoucherBatch.objects.get().label, 'Toko Maria')


class VoucherStaffTests(TestCase):
	def setUp(self):
		self.admin = User.objects.create_superuser('a@x.com')
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.student = User.objects.create_user('e@x.com')
		self.client.force_login(self.admin)
		self.data = {'label': 'Toko Maria, Dili', 'plan': '7d', 'count': '3', 'valid_days': '90'}

	def create(self, **over):
		return self.client.post('/staff/vaucher/', {**self.data, **over})

	def test_roles(self):
		for user in (self.staff, self.student):
			self.client.force_login(user)
			for url in ('/staff/vaucher/', '/staff/vaucher/batch/1/', '/staff/vaucher/batch/1/cetak/'):
				self.assertEqual(self.client.get(url).status_code, 403, f'{user.email} {url}')
			self.assertEqual(self.create().status_code, 403)
		self.assertEqual(VoucherBatch.objects.count(), 0)

	def test_create_redirects_to_print_page_that_shows_codes_exactly_once(self):
		r = self.create()
		batch = VoucherBatch.objects.get()
		self.assertEqual((r.status_code, r['Location']), (302, f'/staff/vaucher/batch/{batch.pk}/cetak/'))
		page = self.client.get(r['Location']).content.decode()
		codes = re.findall(r'data-code="([0-9A-Z-]{14})"', page)
		self.assertEqual(len(codes), 3)
		self.assertIn('<svg', page, 'QR di setiap kartu')
		self.assertIn('Toko Maria, Dili'.split(',')[0], page)
		self.assertIn('dala ida de', page)
		again = self.client.get(r['Location']).content.decode()
		self.assertNotIn('data-code', again)
		for c in codes:
			self.assertNotIn(c, again)
		batch_page = self.client.get(f'/staff/vaucher/batch/{batch.pk}/').content.decode()
		self.assertEqual(len(set(re.findall(r'LFX-\d{4}-000\d', batch_page))), 3)
		for c in codes:
			self.assertNotIn(c, batch_page, 'detail batch tidak pernah memuat kode rahasia')
			self.assertNotIn(c, self.client.get('/staff/vaucher/').content.decode())

	def test_printed_codes_actually_work_and_qr_points_to_prefill_url(self):
		r = self.create()
		page = self.client.get(r['Location']).content.decode()
		code = re.search(r'data-code="([0-9A-Z-]{14})"', page).group(1)
		self.client.force_login(self.student)
		self.assertEqual(post(self.client, '/api/redeem/', {'code': code}).status_code, 200)
		import segno
		qr = segno.make(f'http://testserver/?kode={code}', error='m').svg_inline(scale=3, omitsize=True, dark='#2e3131', border=1)
		self.assertIn(qr, page)

	def test_print_page_of_other_batch_or_after_loss_shows_no_codes(self):
		self.create()
		first = VoucherBatch.objects.get()
		self.create(label='B')
		second = VoucherBatch.objects.exclude(pk=first.pk).get()
		# sesi menyimpan cetakan batch kedua; membuka batch pertama tidak boleh menampilkan apa pun
		page = self.client.get(f'/staff/vaucher/batch/{first.pk}/cetak/').content.decode()
		self.assertNotIn('data-code', page)

	def test_validation(self):
		for bad in ({'count': '0'}, {'count': '501'}, {'count': 'x'}, {'plan': 'nope'}, {'label': '   '}, {'valid_days': '0'},
                    {'valid_days': '5000'}, {'valid_days': 'x'}):
			self.assertEqual(self.create(**bad).status_code, 302)
		self.assertEqual(VoucherBatch.objects.count(), 0)
		self.assertEqual(Voucher.objects.count(), 0)

	def test_label_is_escaped(self):
		self.create(label='<script>alert(1)</script>')
		batch = VoucherBatch.objects.get()
		for url in ('/staff/vaucher/', f'/staff/vaucher/batch/{batch.pk}/'):
			html = self.client.get(url).content.decode()
			self.assertNotIn('<script>alert(1)</script>', html)
			self.assertIn('&lt;script&gt;alert(1)', html)

	def test_void_batch_and_voucher_via_staff_pages(self):
		self.create()
		batch = VoucherBatch.objects.get()
		v = batch.vouchers.first()
		self.assertEqual(self.client.get(f'/staff/vaucher/{v.pk}/kansela/').status_code, 405)
		self.client.post(f'/staff/vaucher/{v.pk}/kansela/')
		v.refresh_from_db()
		self.assertEqual(v.status, 'void')
		self.client.post(f'/staff/vaucher/batch/{batch.pk}/kansela/')
		batch.refresh_from_db()
		self.assertIsNotNone(batch.voided_at)
		self.assertTrue(all(x.status == 'void' for x in Voucher.objects.all()))
		self.assertContains(self.client.get('/staff/vaucher/'), 'Kansela')

	def test_list_shows_usage_and_revenue(self):
		self.create()
		batch = VoucherBatch.objects.get()
		code_rows = [(v.serial, None) for v in batch.vouchers.all()]
		# pakai satu voucher: buat baru agar kodenya diketahui
		b2, rows = services.create_batch(Plan.objects.get(code='7d'), 2, 'Toko B')
		services.redeem(self.student, rows[0][1])
		html = self.client.get('/staff/vaucher/').content.decode()
		self.assertIn('Toko B', html)
		row = [r for r in html.split('<tr>') if 'Toko B' in r][0]
		self.assertIn('<td>3.00</td>', row, 'satu voucher 7 hari terpakai = $3')

	def test_forms_require_csrf(self):
		strict = Client(enforce_csrf_checks=True)
		strict.force_login(self.admin)
		self.assertEqual(strict.post('/staff/vaucher/', self.data).status_code, 403)
		self.assertEqual(strict.post('/staff/vaucher/batch/1/kansela/').status_code, 403)

	def test_dashboard_counts_only_available(self):
		b1, r1 = services.create_batch(Plan.objects.get(code='7d'), 3, 'A')
		services.redeem(self.student, r1[0][1])
		services.void_voucher(Voucher.objects.get(serial=r1[1][0]))
		self.client.force_login(self.staff)
		self.assertEqual(self.client.get('/api/report/stats/').json()['vaucher_livre'], 1)
		self.assertEqual(self.client.get('/api/report/vaucher/').json()['obj'], [1, 1])


class ListOrderingTests(TestCase):
	"""Meta.ordering diabaikan pada query annotate (GROUP BY): urutan harus eksplisit di view."""

	def test_batches_are_newest_first(self):
		admin = User.objects.create_superuser('a@x.com')
		plan = Plan.objects.get(code='7d')
		old, _ = services.create_batch(plan, 1, 'Toko Lama')
		new, _ = services.create_batch(plan, 1, 'Toko Baru')
		VoucherBatch.objects.filter(pk=old.pk).update(created_at=_tz.now() - _td(days=3))
		self.client.force_login(admin)
		html = self.client.get('/staff/vaucher/').content.decode()
		self.assertLess(html.index('Toko Baru'), html.index('Toko Lama'))

	def test_vocab_categories_and_missions_follow_their_configured_order(self):
		from curriculum import seed as curriculum_seed
		from vocab import seed as vocab_seed
		curriculum_seed.run()
		vocab_seed.run()
		staff = User.objects.create_user('s@x.com', is_staff=True)
		self.client.force_login(staff)
		html = self.client.get('/staff/kosakata/').content.decode()
		self.assertLess(html.index('Eskola'), html.index('Merkadu'))
		self.assertLess(html.index('Merkadu'), html.index('Kantór'))
		html = self.client.get('/staff/misaun/').content.decode()
		self.assertLess(html.index('Mai iha aeroportu'), html.index('Rezerva kuartu'))
		self.assertLess(html.index('Rezerva kuartu'), html.index('Mala lakon'))
