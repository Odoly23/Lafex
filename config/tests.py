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
