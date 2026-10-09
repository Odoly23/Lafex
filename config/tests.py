from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings

from curriculum import seed
from main import views as main_views
from users.models import User


class RoleTests(TestCase):
	def setUp(self):
		seed.run()

	def test_roles_exist_and_are_assigned_on_creation(self):
		self.assertEqual(set(Group.objects.values_list('name', flat=True)) >= {'admin', 'staff', 'estudante'}, True)
		self.assertEqual(User.objects.create_user('a@x.com').groups.get().name, 'estudante')
		self.assertEqual(User.objects.create_user('s@x.com', is_staff=True).groups.get().name, 'staff')
		self.assertEqual(User.objects.create_superuser('r@x.com').groups.get().name, 'admin')

	def test_user_without_role_gets_403_page_and_api(self):
		u = User.objects.create_user('norole@x.com')
		u.groups.clear()
		self.client.force_login(u)
		for url in ('/', '/review/', '/mission/tourist-airport/'):
			self.assertEqual(self.client.get(url).status_code, 403, url)
		self.assertEqual(self.client.get('/api/me/').status_code, 403)
		self.assertEqual(self.client.post('/api/sessions/', {}, content_type='application/json').status_code, 403)

	def test_any_matching_group_counts_not_only_the_first(self):
		u = User.objects.create_user('multi@x.com')
		u.groups.clear()
		u.groups.add(Group.objects.get_or_create(name='other')[0], Group.objects.get(name='estudante'))
		self.client.force_login(u)
		self.assertEqual(self.client.get('/').status_code, 200)

	def test_navbar_admin_link_only_for_staff_and_admin(self):
		self.client.force_login(User.objects.create_user('st@x.com'))
		self.assertNotContains(self.client.get('/'), 'href="/admin/"')
		self.client.force_login(User.objects.create_user('staff@x.com', is_staff=True))
		self.assertContains(self.client.get('/'), 'href="/admin/"')

	def test_login_page_redirects_authenticated_user_home(self):
		self.client.force_login(User.objects.create_user('a@x.com'))
		r = self.client.get('/login/')
		self.assertEqual((r.status_code, r['Location']), (302, '/'))


class ErrorPageTests(TestCase):
	@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
	def test_custom_404_page(self):
		r = self.client.get('/tidak-ada/')
		self.assertEqual(r.status_code, 404)
		self.assertContains(r, 'Pájina la hetan', status_code=404)

	def test_500_page_is_static_and_has_right_status(self):
		r = main_views.error_500(RequestFactory().get('/'))
		self.assertEqual(r.status_code, 500)
		self.assertIn(b'500', r.content)


class SystemSettingTests(TestCase):
	def setUp(self):
		seed.run()
		self.admin = User.objects.create_superuser('a@x.com')
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.estudante = User.objects.create_user('e@x.com')

	def form_data(self, **over):
		from billing.models import Plan
		data = {'tutor_prompt_extra': 'Pakai contoh Timor-Leste.', 'payments_required': 'on',
                'free_turns_per_day': '7', 'paid_turns_per_day': '99'}
		plans = list(Plan.objects.order_by('sort'))
		data.update({'plan-TOTAL_FORMS': str(len(plans)), 'plan-INITIAL_FORMS': str(len(plans)),
                     'plan-MIN_NUM_FORMS': '0', 'plan-MAX_NUM_FORMS': '1000'})
		for i, p in enumerate(plans):
			data.update({f'plan-{i}-id': str(p.pk), f'plan-{i}-label': p.label, f'plan-{i}-price_usd': str(p.price_usd),
                         f'plan-{i}-hours': str(p.hours), f'plan-{i}-active': 'on'})
		data.update(over)
		return data

	def test_defaults_and_singleton(self):
		from .models import SystemSetting
		s = SystemSetting.load()
		self.assertEqual((s.payments_required, s.free_turns_per_day, s.paid_turns_per_day, s.pk), (True, 5, 150, 1))
		SystemSetting(tutor_prompt_extra='x').save()
		SystemSetting(tutor_prompt_extra='y').save()
		self.assertEqual(SystemSetting.objects.count(), 1)

	def test_only_admin_can_open_or_post(self):
		for user in (self.staff, self.estudante):
			self.client.force_login(user)
			self.assertEqual(self.client.get('/staff/pengaturan/').status_code, 403)
			self.assertEqual(self.client.post('/staff/pengaturan/', self.form_data()).status_code, 403)

	def test_admin_updates_prompt_limits_and_prices(self):
		from billing.models import Plan
		from .models import SystemSetting
		self.client.force_login(self.admin)
		self.assertEqual(self.client.get('/staff/pengaturan/').status_code, 200)
		first = Plan.objects.order_by('sort').first()
		data = self.form_data(**{'plan-0-price_usd': '1.50'})
		r = self.client.post('/staff/pengaturan/', data)
		self.assertEqual(r.status_code, 302)
		s = SystemSetting.load()
		self.assertEqual((s.tutor_prompt_extra, s.free_turns_per_day, s.paid_turns_per_day), ('Pakai contoh Timor-Leste.', 7, 99))
		first.refresh_from_db()
		self.assertEqual(str(first.price_usd), '1.50')

	def test_validation_rejects_bad_input(self):
		from .models import SystemSetting
		self.client.force_login(self.admin)
		for over in ({'free_turns_per_day': '-1'}, {'paid_turns_per_day': 'abc'}, {'tutor_prompt_extra': 'x' * 2001},
                     {'plan-0-price_usd': '-5'}, {'plan-0-hours': '0'}):
			before = SystemSetting.load().free_turns_per_day
			r = self.client.post('/staff/pengaturan/', self.form_data(**over))
			self.assertEqual(r.status_code, 200, over)
			self.assertEqual(SystemSetting.load().free_turns_per_day, before, over)

	def test_unchecking_payments_required_means_free_mode(self):
		from billing import services as billing
		from .models import SystemSetting
		self.assertFalse(billing.has_access(self.estudante))
		data = self.form_data()
		del data['payments_required']  # checkbox tidak dicentang
		self.client.force_login(self.admin)
		self.client.post('/staff/pengaturan/', data)
		self.assertFalse(SystemSetting.load().payments_required)
		self.assertTrue(billing.has_access(self.estudante))
		self.assertEqual(billing.daily_limit(self.estudante), 99)
		self.client.force_login(self.estudante)
		me = self.client.get('/api/me/').json()
		self.assertTrue(me['free_mode'] and me['access'])
		self.assertContains(self.client.get('/'), 'btn-redeem')  # kartu voucher tetap ada di HTML; JS menyembunyikannya
		self.assertEqual(self.client.get('/api/review/').status_code, 200, 'review terbuka di mode gratis tanpa paket')

	def test_review_locked_again_when_payments_required(self):
		self.client.force_login(self.estudante)
		self.assertEqual(self.client.get('/api/review/').status_code, 402)

	def test_free_mode_review_gets_short_offline_expiry(self):
		from .models import SystemSetting
		from django.utils import timezone
		s = SystemSetting.load()
		s.payments_required = False
		s.save()
		self.client.force_login(self.estudante)
		exp = self.client.get('/api/review/').json()['expires_at']
		from django.utils.dateparse import parse_datetime
		delta = parse_datetime(exp) - timezone.now()
		self.assertTrue(timezone.timedelta(days=6) < delta <= timezone.timedelta(days=7))
