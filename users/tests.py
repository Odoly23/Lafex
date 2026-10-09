import re
from datetime import timedelta

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import LoginCode, User


def post(client, url, data):
	return client.post(url, data, content_type='application/json')


class LoginCodeTests(TestCase):
	def request_code(self, email='Maria@Example.com', client=None):
		client = client or self.client
		r = post(client, '/api/auth/request/', {'email': email})
		code = re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1) if r.status_code == 200 else None
		return r, code

	def test_code_is_emailed_and_hashed(self):
		r, code = self.request_code()
		self.assertEqual(r.status_code, 200)
		self.assertEqual(mail.outbox[-1].to, ['maria@example.com'])  # email dinormalkan
		row = LoginCode.objects.get()
		self.assertNotIn(code, row.code_hash)
		self.assertEqual(len(row.code_hash), 64)

	def test_invalid_email_rejected(self):
		for bad in ('', 'nope', 'a@b', None, 123):
			self.assertEqual(post(self.client, '/api/auth/request/', {'email': bad}).status_code, 400, bad)
		self.assertEqual(len(mail.outbox), 0)

	def test_login_creates_user_then_reuses_it(self):
		_, code = self.request_code()
		r = post(self.client, '/api/auth/verify/', {'email': 'MARIA@example.com', 'code': code})
		self.assertEqual(r.status_code, 200)
		self.assertTrue(r.json()['new_user'])
		self.assertEqual(self.client.get('/').status_code, 200)  # sesi aktif, bukan redirect
		c2 = Client()
		_, code2 = self.request_code(client=c2)
		r2 = post(c2, '/api/auth/verify/', {'email': 'maria@example.com', 'code': code2})
		self.assertFalse(r2.json()['new_user'])
		self.assertEqual(User.objects.count(), 1)

	def test_code_is_single_use(self):
		_, code = self.request_code()
		self.assertEqual(post(self.client, '/api/auth/verify/', {'email': 'maria@example.com', 'code': code}).status_code, 200)
		self.assertEqual(post(Client(), '/api/auth/verify/', {'email': 'maria@example.com', 'code': code}).status_code, 400)

	def test_wrong_code_locks_after_max_attempts(self):
		_, code = self.request_code()
		wrong = '000000' if code != '000000' else '111111'
		for _ in range(5):
			self.assertEqual(post(self.client, '/api/auth/verify/', {'email': 'maria@example.com', 'code': wrong}).status_code, 400)
		r = post(self.client, '/api/auth/verify/', {'email': 'maria@example.com', 'code': code})
		self.assertEqual(r.status_code, 400, 'kode benar pun ditolak setelah 5 tebakan salah')
		self.assertEqual(User.objects.count(), 0)

	def test_expired_code_rejected(self):
		_, code = self.request_code()
		LoginCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
		self.assertEqual(post(self.client, '/api/auth/verify/', {'email': 'maria@example.com', 'code': code}).status_code, 400)

	def test_malformed_code_rejected(self):
		self.request_code()
		for bad in ('12345', '1234567', 'abcdef', '', None):
			self.assertEqual(post(self.client, '/api/auth/verify/', {'email': 'maria@example.com', 'code': bad}).status_code, 400)

	def test_rate_limit_per_email(self):
		for _ in range(5):
			self.assertEqual(post(self.client, '/api/auth/request/', {'email': 'a@x.com'}).status_code, 200)
		self.assertEqual(post(self.client, '/api/auth/request/', {'email': 'a@x.com'}).status_code, 429)
		self.assertEqual(post(self.client, '/api/auth/request/', {'email': 'other@x.com'}).status_code, 200)

	def test_no_user_enumeration(self):
		User.objects.create_user('known@x.com')
		a = post(self.client, '/api/auth/request/', {'email': 'known@x.com'})
		b = post(self.client, '/api/auth/request/', {'email': 'unknown@x.com'})
		self.assertEqual((a.status_code, a.json()), (b.status_code, b.json()))

	def test_inactive_user_cannot_login(self):
		User.objects.create_user('off@x.com', is_active=False)
		_, code = self.request_code('off@x.com')
		self.assertEqual(post(self.client, '/api/auth/verify/', {'email': 'off@x.com', 'code': code}).status_code, 400)

	def test_csrf_is_enforced(self):
		strict = Client(enforce_csrf_checks=True)
		self.assertEqual(post(strict, '/api/auth/request/', {'email': 'a@x.com'}).status_code, 403)

	def test_logout(self):
		_, code = self.request_code()
		post(self.client, '/api/auth/verify/', {'email': 'maria@example.com', 'code': code})
		self.assertEqual(post(self.client, '/api/auth/logout/', {}).status_code, 200)
		self.assertEqual(self.client.get('/api/me/').status_code, 401)

	def test_user_has_unusable_password(self):
		u = User.objects.create_user('p@x.com')
		self.assertFalse(u.has_usable_password())

	def test_new_user_gets_estudante_role(self):
		_, code = self.request_code()
		post(self.client, "/api/auth/verify/", {"email": "maria@example.com", "code": code})
		self.assertEqual(User.objects.get().groups.get().name, "estudante")
		self.assertEqual(self.client.get("/api/me/").status_code, 200)


class StudentManageTests(TestCase):
	def setUp(self):
		from curriculum import seed
		seed.run()
		self.admin = User.objects.create_superuser('a@x.com')
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.student = User.objects.create_user('e@x.com')

	def post(self, user, pk, data):
		self.client.force_login(user)
		return self.client.post(f'/staff/siswa/{pk}/', data)

	def test_access_by_role(self):
		self.client.force_login(self.student)
		self.assertEqual(self.client.get(f'/staff/siswa/{self.student.pk}/').status_code, 403)
		for u in (self.staff, self.admin):
			self.client.force_login(u)
			self.assertEqual(self.client.get(f'/staff/siswa/{self.student.pk}/').status_code, 200)

	def test_only_students_are_editable_here(self):
		self.client.force_login(self.admin)
		for other in (self.staff, self.admin):
			self.assertEqual(self.client.get(f'/staff/siswa/{other.pk}/').status_code, 404, other.email)

	def test_staff_edits_basic_fields(self):
		r = self.post(self.staff, self.student.pk, {'name': 'Maria', 'level': 'B1', 'is_active': 'on'})
		self.assertEqual(r.status_code, 302)
		self.student.refresh_from_db()
		self.assertEqual((self.student.name, self.student.level, self.student.is_active), ('Maria', 'B1', True))
		self.post(self.staff, self.student.pk, {'name': 'Maria', 'level': 'B1'})  # is_active tidak dicentang
		self.student.refresh_from_db()
		self.assertFalse(self.student.is_active)

	def test_staff_cannot_grant_plan_but_admin_can(self):
		from billing import services as billing
		from billing.models import Plan
		plan = Plan.objects.get(code='7d')
		self.client.force_login(self.staff)
		self.assertNotIn('grant_plan', self.client.get(f'/staff/siswa/{self.student.pk}/').content.decode())
		self.post(self.staff, self.student.pk, {'name': '', 'level': 'A1', 'is_active': 'on', 'grant_plan': plan.pk})
		self.assertFalse(billing.is_active(self.student), 'staff mengirim grant_plan manual tetap diabaikan')
		self.post(self.admin, self.student.pk, {'name': '', 'level': 'A1', 'is_active': 'on', 'grant_plan': plan.pk})
		self.assertTrue(billing.is_active(self.student))

	def test_invalid_level_rejected(self):
		r = self.post(self.admin, self.student.pk, {'name': 'x', 'level': 'Z9', 'is_active': 'on'})
		self.assertEqual(r.status_code, 200)
		self.student.refresh_from_db()
		self.assertEqual(self.student.level, 'A1')

	def test_list_links_to_edit(self):
		self.client.force_login(self.staff)
		self.assertIn(f'/staff/siswa/{self.student.pk}/', self.client.get('/staff/siswa/').content.decode())
