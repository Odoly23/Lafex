from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from users.models import User

from . import services
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
		self.assertEqual(Voucher.objects.get(code=code).used_by, self.user)

	def test_create_vouchers_command(self):
		from io import StringIO
		from django.core.management import call_command
		out = StringIO()
		call_command('create_vouchers', '1d', '3', stdout=out)
		self.assertEqual(len(out.getvalue().split()), 3)
