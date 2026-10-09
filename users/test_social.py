from contextlib import ExitStack
from unittest import mock
from urllib.parse import parse_qs, urlparse

from allauth.socialaccount.providers.facebook import flows as fb_flows
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter
from django.test import Client, TestCase, override_settings

from .models import User

PROVIDERS = {
    'google': {'APPS': [{'client_id': 'GID', 'secret': 'GSECRET', 'key': ''}], 'SCOPE': ['profile', 'email']},
    'facebook': {'APPS': [{'client_id': 'FID', 'secret': 'FSECRET', 'key': ''}], 'METHOD': 'oauth2',
                 'SCOPE': ['email', 'public_profile'], 'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name'],
                 'VERIFIED_EMAIL': False},
}
GOOGLE_PROFILE = {'id': 'g-1', 'email': 'maria@gmail.com', 'verified_email': True, 'name': 'Maria da Silva',
                  'given_name': 'Maria', 'family_name': 'da Silva'}


def logged_in(client):
	return '_auth_user_id' in client.session


@override_settings(SOCIALACCOUNT_PROVIDERS=PROVIDERS)
class SocialLoginTests(TestCase):
	def start(self, provider='google', next_url=None, client=None):
		client = client or self.client
		client.get('/login/')  # cookie CSRF
		data = {'next': next_url} if next_url else {}
		r = client.post(f'/accounts/{provider}/login/?process=login', data)
		return r, parse_qs(urlparse(r['Location']).query).get('state', [None])[0] if r.status_code == 302 else None

	def callback(self, provider, state, profile, client=None):
		client = client or self.client
		with ExitStack() as stack:
			stack.enter_context(mock.patch.object(OAuth2Adapter, 'get_access_token_data', return_value={'access_token': 'tok'}))
			if provider == 'google':
				stack.enter_context(mock.patch.object(GoogleOAuth2Adapter, '_fetch_user_info', return_value=profile))
			else:
				def fake(request, prov, token):
					return prov.sociallogin_from_response(request, profile)
				stack.enter_context(mock.patch.object(fb_flows, 'complete_login', side_effect=fake))
			return client.get(f'/accounts/{provider}/login/callback/?code=abc&state={state}')

	# ---- tampilan ----
	def test_login_page_shows_buttons_with_csrf_post_forms(self):
		html = self.client.get('/login/?next=/profil/').content.decode()
		for pid, label in (('google', 'Google'), ('facebook', 'Facebook')):
			self.assertIn(f'action="/accounts/{pid}/login/?process=login&amp;next=%2Fprofil%2F"', html)
			self.assertIn(f'Tama ho {label}', html)
		self.assertIn('csrfmiddlewaretoken', html)

	@override_settings(SOCIALACCOUNT_PROVIDERS={})
	def test_no_buttons_when_nothing_is_configured(self):
		html = self.client.get('/login/').content.decode()
		self.assertNotIn('/accounts/google/', html)
		self.assertNotIn('Tama ho Google', html)
		self.assertIn('id="form-email"', html, 'login email tetap ada')

	@override_settings(SOCIALACCOUNT_PROVIDERS={'google': PROVIDERS['google']})
	def test_only_configured_provider_is_shown(self):
		html = self.client.get('/login/').content.decode()
		self.assertIn('Tama ho Google', html)
		self.assertNotIn('Tama ho Facebook', html)

	def test_unsafe_next_is_dropped_from_the_form(self):
		for bad in ('https://evil.example/', '//evil.example', 'javascript:alert(1)'):
			html = self.client.get('/login/', {'next': bad}).content.decode()
			self.assertNotIn('evil.example', html, bad)
			self.assertNotIn('next=', html.split('id="social"')[1].split('id="form-email"')[0], bad)

	# ---- mulai login ----
	def test_post_redirects_to_google_with_our_client_and_callback(self):
		r, state = self.start('google')
		self.assertEqual(r.status_code, 302)
		loc = urlparse(r['Location'])
		q = parse_qs(loc.query)
		self.assertEqual((loc.netloc, loc.path), ('accounts.google.com', '/o/oauth2/v2/auth'))
		self.assertEqual(q['client_id'], ['GID'])
		self.assertEqual(q['redirect_uri'], ['http://testserver/accounts/google/login/callback/'])
		self.assertIn('email', q['scope'][0])
		self.assertTrue(state)

	def test_post_redirects_to_facebook(self):
		r, _ = self.start('facebook')
		loc = urlparse(r['Location'])
		self.assertTrue(loc.netloc.endswith('facebook.com'))
		self.assertEqual(parse_qs(loc.query)['client_id'], ['FID'])

	def test_get_does_not_start_login_and_csrf_is_enforced(self):
		r = self.client.get('/accounts/google/login/?process=login')
		self.assertNotIn('google.com', r.get('Location', ''))
		strict = Client(enforce_csrf_checks=True)
		self.assertEqual(strict.post('/accounts/google/login/?process=login').status_code, 403)

	# ---- Google ----
	def test_google_first_login_registers_automatically_as_student(self):
		_, state = self.start('google')
		r = self.callback('google', state, GOOGLE_PROFILE)
		self.assertEqual((r.status_code, r['Location']), (302, '/'))
		user = User.objects.get(email='maria@gmail.com')
		self.assertTrue(logged_in(self.client))
		self.assertEqual(user.name, 'Maria da Silva')
		self.assertEqual([g.name for g in user.groups.all()], ['estudante'])
		self.assertFalse(user.has_usable_password())
		self.assertEqual(self.client.get('/api/me/').status_code, 200)
		self.assertFalse(user.placement_done)

	def test_second_google_login_reuses_account(self):
		_, state = self.start('google')
		self.callback('google', state, GOOGLE_PROFILE)
		self.client.post('/api/auth/logout/', content_type='application/json')
		_, state = self.start('google')
		self.callback('google', state, GOOGLE_PROFILE)
		self.assertEqual(User.objects.filter(email='maria@gmail.com').count(), 1)
		self.assertTrue(logged_in(self.client))

	def test_next_is_honored_after_login(self):
		_, state = self.start('google', next_url='/?kode=ABCD-EFGH-JKMN')
		r = self.callback('google', state, GOOGLE_PROFILE)
		self.assertEqual(r['Location'], '/?kode=ABCD-EFGH-JKMN')

	def test_google_connects_to_existing_email_account(self):
		existing = User.objects.create_user('maria@gmail.com')
		existing.points = 42
		existing.save()
		_, state = self.start('google')
		self.callback('google', state, GOOGLE_PROFILE)
		self.assertEqual(User.objects.count(), 1)
		self.assertEqual(int(self.client.session['_auth_user_id']), existing.pk)
		existing.refresh_from_db()
		self.assertEqual(existing.points, 42)

	def test_unverified_google_email_is_not_merged_into_existing_account(self):
		victim = User.objects.create_user('maria@gmail.com')
		_, state = self.start('google')
		r = self.callback('google', state, {**GOOGLE_PROFILE, 'verified_email': False})
		self.assertFalse(logged_in(self.client) and int(self.client.session['_auth_user_id']) == victim.pk)

	# ---- Facebook ----
	def test_facebook_first_login_registers_automatically(self):
		_, state = self.start('facebook')
		profile = {'id': 'f-1', 'email': 'joao@example.com', 'name': 'João Pereira', 'first_name': 'João', 'last_name': 'Pereira'}
		r = self.callback('facebook', state, profile)
		self.assertEqual(r.status_code, 302)
		user = User.objects.get(email='joao@example.com')
		self.assertTrue(logged_in(self.client))
		self.assertEqual(user.name, 'João Pereira')
		self.assertEqual([g.name for g in user.groups.all()], ['estudante'])

	def test_facebook_never_takes_over_an_existing_account_by_email(self):
		"""Email Facebook dianggap tidak terverifikasi: penyerang tidak bisa masuk ke akun korban dengan email yang sama."""
		victim = User.objects.create_user('korban@example.com')
		_, state = self.start('facebook')
		profile = {'id': 'evil', 'email': 'korban@example.com', 'name': 'Penyerang', 'first_name': 'P', 'last_name': 'S'}
		self.callback('facebook', state, profile)
		authed = logged_in(self.client)
		self.assertFalse(authed and int(self.client.session['_auth_user_id']) == victim.pk)
		self.assertEqual(User.objects.filter(email='korban@example.com').count(), 1)

	def test_missing_email_is_refused_with_message_and_creates_nothing(self):
		_, state = self.start('facebook')
		r = self.callback('facebook', state, {'id': 'f-2', 'name': 'Tanpa Email', 'first_name': 'T', 'last_name': 'E'})
		self.assertEqual((r.status_code, r['Location']), (302, '/login/?error=social_no_email'))
		self.assertEqual(User.objects.count(), 0)
		self.assertFalse(logged_in(self.client))

	# ---- kegagalan / pembatalan ----
	def test_cancelled_and_failed_authorisation_return_to_login_with_message(self):
		_, state = self.start('google')
		r = self.client.get(f'/accounts/google/login/callback/?error=access_denied&state={state}')
		self.assertEqual(r['Location'], '/login/?error=social_cancelled')
		_, state = self.start('google')
		r = self.client.get(f'/accounts/google/login/callback/?error=server_error&state={state}')
		self.assertEqual(r['Location'], '/login/?error=social_error')
		self.assertFalse(logged_in(self.client))

	def test_invalid_state_is_rejected(self):
		self.start('google')
		r = self.callback('google', 'bukan-state-yang-benar', GOOGLE_PROFILE)
		self.assertFalse(logged_in(self.client))
		self.assertEqual(User.objects.count(), 0)

	def test_login_error_messages_exist_in_tetun(self):
		from main.strings import TETUN
		for k in ('err_social_error', 'err_social_cancelled', 'err_social_no_email', 'login_with', 'login_or'):
			self.assertIn(k, TETUN)

	def test_inactive_user_cannot_log_in_with_google(self):
		User.objects.create_user('maria@gmail.com', is_active=False)
		_, state = self.start('google')
		self.callback('google', state, GOOGLE_PROFILE)
		self.assertFalse(logged_in(self.client))

	# ---- hanya login sosial: tidak ada jalur password/daftar lokal ----
	def test_local_signup_and_password_views_are_not_exposed(self):
		for url in ('/accounts/password/reset/', '/accounts/email/', '/accounts/password/change/', '/accounts/confirm-email/'):
			self.assertEqual(self.client.get(url).status_code, 404, url)
		r = self.client.post('/accounts/signup/', {'email': 'x@x.com', 'password1': 'abc12345XYZ', 'password2': 'abc12345XYZ'})
		self.assertIn(r.status_code, (302, 404))
		self.assertEqual(User.objects.count(), 0)

	def test_social_login_disabled_for_signup_through_account_adapter(self):
		from .adapters import AccountAdapter
		self.assertFalse(AccountAdapter().is_open_for_signup(None))


class RoleHealingTests(TestCase):
	def test_user_without_role_gets_estudante_when_logging_in_by_code(self):
		from django.core import mail
		import re
		u = User.objects.create_user('x@x.com')
		u.groups.clear()
		self.client.post('/api/auth/request/', {'email': 'x@x.com'}, content_type='application/json')
		code = re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)
		self.client.post('/api/auth/verify/', {'email': 'x@x.com', 'code': code}, content_type='application/json')
		self.assertEqual([g.name for g in u.groups.all()], ['estudante'])
