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
	PAGES = {
        '/staff/': 'staff', '/staff/siswa/': 'staff', '/staff/materi/': 'staff', '/staff/misaun/': 'staff',
        '/staff/kosakata/': 'staff', '/staff/quiz/': 'staff', '/staff/monitoring/chat/': 'staff',
        '/staff/monitoring/pronunciation/': 'staff', '/staff/vaucher/': 'admin', '/staff/pengaturan/': 'admin',
    }

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
		staff_ok = {u for u, r in self.PAGES.items() if r == 'staff'}
		for user, ok in ((self.estudante, set()), (self.staff, staff_ok), (self.admin, set(self.PAGES))):
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

	def test_mission_list_has_edit_links_for_staff_role_even_without_is_staff(self):
		from curriculum.models import Mission
		plain = User.objects.create_user('docente@x.com')
		plain.groups.set(self.staff.groups.all())  # peran staff tanpa flag is_staff (tanpa akses Django admin)
		self.client.force_login(plain)
		html = self.client.get('/staff/misaun/').content.decode()
		self.assertIn(f"/staff/misaun/{Mission.objects.first().pk}/", html)
		self.assertNotIn('href="/admin/"', html, 'tautan Django admin hanya untuk is_staff')

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


class DashboardStatsTests(TestCase):
	def setUp(self):
		seed.run()
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.a = User.objects.create_user('a@x.com')
		self.b = User.objects.create_user('b@x.com')

	def test_active_today_counts_distinct_students_only(self):
		from progress import services as progress
		progress.award(self.a, 'quiz', 1)
		progress.award(self.a, 'vocab', 1)          # siswa yang sama: dihitung sekali
		progress.award(self.staff, 'quiz', 1)       # staff tidak dihitung
		old = progress.award(self.b, 'quiz', 1)
		from progress.models import Activity
		from django.utils import timezone
		Activity.objects.filter(user=self.b).update(created_at=timezone.now() - timezone.timedelta(days=3))
		self.client.force_login(self.staff)
		self.assertEqual(self.client.get('/api/report/stats/').json()['aktif_ohin'], 1)

	def test_total_chat_counts_student_messages_only(self):
		from curriculum.models import Mission
		from tutor.models import Session, Turn
		s = Session.objects.create(user=self.a, mission=Mission.objects.get(slug='tourist-hotel'), level_start='A1')
		Turn.objects.create(session=s, idx=0, role='assistant', text='Hello')
		Turn.objects.create(session=s, idx=1, role='user', text='Hi')
		Turn.objects.create(session=s, idx=2, role='assistant', text='Name?')
		Turn.objects.create(session=s, idx=3, role='user', text='Maria')
		self.client.force_login(self.staff)
		self.assertEqual(self.client.get('/api/report/stats/').json()['total_chat'], 2)


class MonitoringTests(TestCase):
	def setUp(self):
		seed.run()
		from pronounce import seed as pron_seed
		pron_seed.run()
		from curriculum.models import Mission
		self.mission = Mission.objects.get(slug='tourist-hotel')
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.a = User.objects.create_user('a@x.com')
		self.b = User.objects.create_user('b@x.com')

	def session(self, user, user_msgs=2):
		from tutor.models import Session, Turn
		s = Session.objects.create(user=user, mission=self.mission, level_start='A1', score=70, level_end='A2')
		Turn.objects.create(session=s, idx=0, role='assistant', text='Welcome to the hotel')
		for i in range(user_msgs):
			Turn.objects.create(session=s, idx=1 + 2 * i, role='user', text=f'My message {i}', correction='Better one' if i == 0 else '')
			Turn.objects.create(session=s, idx=2 + 2 * i, role='assistant', text='Reply')
		return s

	def test_chat_list_hides_empty_sessions_and_estudante_gets_403(self):
		full, empty = self.session(self.a), self.session(self.b, user_msgs=0)
		self.client.force_login(self.a)
		self.assertEqual(self.client.get('/staff/monitoring/chat/').status_code, 403)
		self.client.force_login(self.staff)
		html = self.client.get('/staff/monitoring/chat/').content.decode()
		self.assertIn(f'/staff/monitoring/chat/{full.pk}/', html)
		self.assertNotIn(f'/staff/monitoring/chat/{empty.pk}/', html)

	def test_chat_detail_shows_transcript_and_writes_audit_log(self):
		from .models import MonitorLog
		s = self.session(self.a)
		self.client.force_login(self.staff)
		html = self.client.get(f'/staff/monitoring/chat/{s.pk}/').content.decode()
		for text in ('Welcome to the hotel', 'My message 0', 'Better one'):
			self.assertIn(text, html)
		log = MonitorLog.objects.get()
		self.assertEqual((log.viewer, log.session), (self.staff, s))
		self.client.get(f'/staff/monitoring/chat/{s.pk}/')
		self.assertEqual(MonitorLog.objects.count(), 2, 'setiap pembukaan dicatat')
		self.assertEqual(self.client.get('/staff/monitoring/chat/99999/').status_code, 404)

	def test_chat_detail_forbidden_for_estudante_and_not_logged(self):
		from .models import MonitorLog
		s = self.session(self.a)
		self.client.force_login(self.b)
		self.assertEqual(self.client.get(f'/staff/monitoring/chat/{s.pk}/').status_code, 403)
		self.assertEqual(MonitorLog.objects.count(), 0, 'akses ditolak tidak dicatat sebagai pembukaan')

	def test_lowest_pronunciation_first_and_needs_help_flag(self):
		from pronounce.models import PronAttempt, PronPhrase
		phrase = PronPhrase.objects.first()
		c = User.objects.create_user('c@x.com')
		for user, scores in ((self.a, [90, 95, 100]), (self.b, [30, 40, 50]), (c, [10, 20])):
			for sc in scores:
				PronAttempt.objects.create(user=user, phrase=phrase, score=sc)
		PronAttempt.objects.create(user=self.staff, phrase=phrase, score=5)  # staff tidak ikut
		self.client.force_login(self.staff)
		html = self.client.get('/staff/monitoring/pronunciation/').content.decode()
		self.assertLess(html.index('c@x.com'), html.index('b@x.com'))
		self.assertLess(html.index('b@x.com'), html.index('a@x.com'))
		self.assertNotIn('s@x.com</td>', html)
		rows = html.split('<tr>')[1:]
		flag = {('b@x.com' in r, 'c@x.com' in r, 'a@x.com' in r): 'Presiza ajuda' in r for r in rows if 'badge' in r or '@x.com' in r}
		self.assertTrue(flag[(True, False, False)], 'b: rata-rata 40 dengan 3 percobaan => perlu bantuan')
		self.assertFalse(flag[(False, True, False)], 'c: baru 2 percobaan => belum cukup data')
		self.assertFalse(flag[(False, False, True)])

	def test_only_recent_attempts_are_averaged(self):
		from pronounce.models import PronAttempt, PronPhrase
		from django.utils import timezone
		phrase = PronPhrase.objects.first()
		for i in range(25):
			at = PronAttempt.objects.create(user=self.a, phrase=phrase, score=100 if i >= 5 else 0)
			PronAttempt.objects.filter(pk=at.pk).update(created_at=timezone.now() - timezone.timedelta(minutes=30 - i))
		self.client.force_login(self.staff)
		html = self.client.get('/staff/monitoring/pronunciation/').content.decode()
		self.assertIn('<strong>100</strong>', html, '20 percobaan terakhir semuanya 100')
