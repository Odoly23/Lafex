from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from curriculum import seed
from users.models import User

from . import services
from .models import Activity, Certificate


def post(client, url, data=None):
	return client.post(url, data or {}, content_type='application/json')


class StreakAndPointsTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('a@x.com')

	def test_first_activity_starts_streak_and_adds_points(self):
		services.award(self.user, 'quiz', 7)
		self.user.refresh_from_db()
		self.assertEqual((self.user.points, self.user.streak, self.user.best_streak), (7, 1, 1))
		self.assertEqual(Activity.objects.count(), 1)

	def test_same_day_does_not_increase_streak(self):
		services.award(self.user, 'quiz', 1)
		services.award(self.user, 'vocab', 1)
		self.user.refresh_from_db()
		self.assertEqual((self.user.points, self.user.streak), (2, 1))

	def test_consecutive_days_increase_and_gap_resets(self):
		today = timezone.localdate()
		User.objects.filter(pk=self.user.pk).update(streak=3, best_streak=3, last_active=today - timedelta(days=1))
		services.award(self.user, 'quiz', 0)
		self.assertEqual((self.user.streak, self.user.best_streak), (4, 4))
		User.objects.filter(pk=self.user.pk).update(last_active=today - timedelta(days=2))
		self.user.refresh_from_db()
		services.award(self.user, 'quiz', 0)
		self.assertEqual((self.user.streak, self.user.best_streak), (1, 4), 'putus: mulai lagi, rekor tetap')

	def test_displayed_streak_is_zero_when_broken(self):
		today = timezone.localdate()
		self.user.streak, self.user.last_active = 5, today - timedelta(days=1)
		self.assertEqual(services.current_streak(self.user), 5)
		self.user.last_active = today - timedelta(days=2)
		self.assertEqual(services.current_streak(self.user), 0)
		self.user.last_active = None
		self.assertEqual(services.current_streak(self.user), 0)

	def test_negative_points_are_ignored(self):
		services.award(self.user, 'quiz', -50)
		self.user.refresh_from_db()
		self.assertEqual(self.user.points, 0)


class CertificateTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('a@x.com')

	def test_only_from_a2_and_once_per_level(self):
		self.assertIsNone(services.issue_certificate(self.user, 'A1'))
		self.assertIsNone(services.issue_certificate(self.user, 'ZZ'))
		c1 = services.issue_certificate(self.user, 'B1')
		c2 = services.issue_certificate(self.user, 'B1')
		self.assertEqual(c1.pk, c2.pk)
		self.assertRegex(c1.code, r'^LFX-[0-9A-F]{8}$')
		self.assertEqual(Certificate.objects.count(), 1)

	def test_public_page_shows_current_name_without_email(self):
		cert = services.issue_certificate(self.user, 'A2')
		self.assertContains(self.client.get(f'/sertifikat/{cert.code}/'), 'Estudante Lafex')
		self.user.name = 'Maria da Silva'
		self.user.save()
		r = self.client.get(f'/sertifikat/{cert.code.lower()}/')
		self.assertContains(r, 'Maria da Silva')
		self.assertContains(r, 'A2')
		self.assertNotContains(r, 'a@x.com')
		self.assertEqual(self.client.get('/sertifikat/LFX-00000000/').status_code, 404)


class ProfileTests(TestCase):
	def test_requires_login_and_page_has_no_personal_data(self):
		self.assertEqual(self.client.get('/api/profile/').status_code, 401)
		self.assertEqual(self.client.get('/profil/').status_code, 302)
		u = User.objects.create_user('secret@x.com', is_staff=False)
		u.name = 'Nama Rahasia'
		u.save()
		self.client.force_login(u)
		html = self.client.get('/profil/').content.decode()
		self.assertNotIn('secret@x.com', html)
		self.assertNotIn('Nama Rahasia', html)

	def test_get_and_update_name(self):
		u = User.objects.create_user('a@x.com')
		self.client.force_login(u)
		p = self.client.get('/api/profile/').json()
		self.assertEqual((p['level'], p['points'], p['streak'], p['certificates']), ('A1', 0, 0, []))
		r = post(self.client, '/api/profile/', {'name': '  Maria    da   Silva  ' + 'x' * 200})
		self.assertEqual(r.status_code, 200)
		u.refresh_from_db()
		self.assertTrue(u.name.startswith('Maria da Silva x'))
		self.assertLessEqual(len(u.name), 80)

	def test_non_string_name_does_not_crash(self):
		self.client.force_login(User.objects.create_user('a@x.com'))
		self.assertEqual(post(self.client, '/api/profile/', {'name': 123}).status_code, 200)
		self.assertEqual(post(self.client, '/api/profile/', {}).status_code, 200)
