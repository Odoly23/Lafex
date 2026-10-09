from django.test import Client, TestCase

from billing import services as billing
from curriculum import seed
from tutor.models import Session
from users.models import User

API = ['/api/report/stats/', '/api/report/sesaun-daily/', '/api/report/levels/', '/api/report/misaun/', '/api/report/vaucher/']


class ReportApiTests(TestCase):
	def setUp(self):
		seed.run()
		self.estudante = User.objects.create_user('e@x.com')
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.admin = User.objects.create_superuser('a@x.com')

	def test_permission_matrix(self):
		for url in API:
			self.assertEqual(self.client.get(url).status_code, 401, url)
			self.client.force_login(self.estudante)
			self.assertEqual(self.client.get(url).status_code, 403, url)
			self.client.force_login(self.staff)
			self.assertEqual(self.client.get(url).status_code, 200, url)
			self.client.force_login(self.admin)
			self.assertEqual(self.client.get(url).status_code, 200, url)
			self.client.logout()

	def test_basic_auth_is_not_accepted(self):
		import base64
		self.staff.set_password('pw-staff-123')
		self.staff.save()
		token = base64.b64encode(b's@x.com:pw-staff-123').decode()
		r = Client().get('/api/report/stats/', HTTP_AUTHORIZATION='Basic ' + token)
		self.assertEqual(r.status_code, 401)
		self.assertEqual(r['WWW-Authenticate'], 'Session')

	def test_error_shape_is_uniform(self):
		self.assertEqual(self.client.get('/api/report/stats/').json(), {'error': 'unauthorized'})
		self.client.force_login(self.estudante)
		self.assertEqual(self.client.get('/api/report/stats/').json(), {'error': 'forbidden'})

	def test_authenticated_post_requires_csrf(self):
		strict = Client(enforce_csrf_checks=True)
		strict.force_login(self.estudante)
		r = strict.post('/api/redeem/', {'code': 'X'}, content_type='application/json')
		self.assertEqual(r.status_code, 403)

	def test_chart_data_shapes(self):
		self.client.force_login(self.staff)
		daily = self.client.get('/api/report/sesaun-daily/').json()
		self.assertEqual((len(daily['label']), len(daily['obj'])), (14, 14))
		self.assertEqual(sum(daily['obj']), 0)
		levels = self.client.get('/api/report/levels/').json()
		self.assertEqual(levels['label'], ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])
		self.assertEqual(levels['obj'][0], 1, 'hanya estudante dihitung (staff/admin tidak)')
		stats = self.client.get('/api/report/stats/').json()
		self.assertEqual((stats['siswa'], stats['sesaun'], stats['pakote_ativu'], stats['vaucher_livre']), (1, 0, 0, 0))

	def test_stats_and_missions_reflect_activity(self):
		from curriculum.models import Mission
		from django.utils import timezone
		m = Mission.objects.get(slug='tourist-hotel')
		for score in (60, 80):
			Session.objects.create(user=self.estudante, mission=m, level_start='A1', finished_at=timezone.now(), score=score)
		Session.objects.create(user=self.estudante, mission=m, level_start='A1')  # belum selesai: tidak dihitung
		billing.redeem(self.estudante, billing.create_vouchers('1d', 2)[0])
		self.client.force_login(self.staff)
		stats = self.client.get('/api/report/stats/').json()
		self.assertEqual((stats['sesaun'], stats['pakote_ativu'], stats['vaucher_livre']), (2, 1, 1))
		ms = self.client.get('/api/report/misaun/').json()
		i = ms['label'].index(m.title_tet)
		self.assertEqual((ms['obj'][i], ms['avg'][i]), (2, 70))
		self.assertEqual(sum(self.client.get('/api/report/sesaun-daily/').json()['obj']), 2)
		self.assertEqual(self.client.get('/api/report/vaucher/').json()['obj'], [1, 1])


class StaffPagesTests(TestCase):
	PAGES = {'/staff/': 'staff', '/staff/siswa/': 'staff', '/staff/misaun/': 'staff', '/staff/vaucher/': 'admin'}

	def setUp(self):
		seed.run()
		self.estudante = User.objects.create_user('e@x.com')
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.admin = User.objects.create_superuser('a@x.com')

	def test_anonymous_redirected_to_login(self):
		for url in self.PAGES:
			r = self.client.get(url)
			self.assertEqual((r.status_code, r['Location'].startswith('/login/')), (302, True), url)

	def test_page_access_by_role(self):
		for user, ok in ((self.estudante, set()), (self.staff, {'/staff/', '/staff/siswa/', '/staff/misaun/'}),
                         (self.admin, set(self.PAGES))):
			self.client.force_login(user)
			for url in self.PAGES:
				self.assertEqual(self.client.get(url).status_code, 200 if url in ok else 403, f'{user.email} {url}')

	def html(self, url='/'):
		"""HTML tanpa blok JSON teks (yang memuat semua teks menu untuk JavaScript)."""
		import re
		return re.sub(r'<script id="t-data".*?</script>', '', self.client.get(url).content.decode(), flags=re.S)

	def test_menu_depends_on_role(self):
		self.client.force_login(self.estudante)
		home = self.html()
		for hidden in ('Painel', 'href="/staff/', 'Vaucher'):
			self.assertNotIn(hidden, home)
		self.assertIn('Revisaun', home)
		self.client.force_login(self.staff)
		home = self.html()
		self.assertIn('/staff/siswa/', home)
		self.assertNotIn('/staff/vaucher/', home)
		self.client.force_login(self.admin)
		self.assertIn('/staff/vaucher/', self.html())

	def test_student_list_shows_only_estudante(self):
		self.client.force_login(self.staff)
		html = self.client.get('/staff/siswa/').content.decode()
		self.assertIn('e@x.com', html)
		self.assertNotIn('s@x.com</td>', html)
		self.assertNotIn('a@x.com</td>', html)

	def test_mission_list_edit_link_only_for_is_staff(self):
		self.client.force_login(self.staff)
		self.assertIn('/admin/curriculum/mission/', self.client.get('/staff/misaun/').content.decode())
		plain = User.objects.create_user('docente@x.com')
		plain.groups.set(self.staff.groups.all())  # peran staff tanpa flag is_staff
		self.client.force_login(plain)
		r = self.client.get('/staff/misaun/')
		self.assertEqual(r.status_code, 200)
		self.assertNotIn('/admin/curriculum/mission/', r.content.decode())

	def test_voucher_generation_flow(self):
		from billing.models import Voucher
		self.client.force_login(self.admin)
		r = self.client.post('/staff/vaucher/', {'plan': '7d', 'count': '3'})
		self.assertEqual(r.status_code, 302)
		self.assertEqual(Voucher.objects.filter(plan__code='7d').count(), 3)
		page = self.client.get('/staff/vaucher/').content.decode()
		for v in Voucher.objects.all():
			self.assertIn(v.code, page)
		self.assertIn('Kódigu foun', page)
		self.assertNotIn('Kódigu foun', self.client.get('/staff/vaucher/').content.decode(), 'kode baru hanya tampil sekali')

	def test_voucher_generation_validation_and_roles(self):
		from billing.models import Voucher
		self.client.force_login(self.admin)
		for bad in ({'plan': '7d', 'count': '0'}, {'plan': '7d', 'count': '201'}, {'plan': '7d', 'count': 'x'},
                    {'plan': 'nope', 'count': '2'}, {'count': '2'}):
			self.client.post('/staff/vaucher/', bad)
		self.assertEqual(Voucher.objects.count(), 0)
		self.client.force_login(self.staff)
		self.assertEqual(self.client.post('/staff/vaucher/', {'plan': '7d', 'count': '2'}).status_code, 403)
		self.assertEqual(Voucher.objects.count(), 0)

	def test_voucher_form_requires_csrf(self):
		strict = Client(enforce_csrf_checks=True)
		strict.force_login(self.admin)
		self.assertEqual(strict.post('/staff/vaucher/', {'plan': '7d', 'count': '2'}).status_code, 403)
