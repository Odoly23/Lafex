import json
from pathlib import Path

from django.contrib.staticfiles import finders
from django.test import TestCase

from users.models import User

from . import seed
from .models import Municipality


def post(client, url, data=None):
	return client.post(url, data or {}, content_type='application/json')


class MunicipalityTests(TestCase):
	def setUp(self):
		seed.run()

	def test_seed_is_idempotent_and_complete(self):
		self.assertEqual(Municipality.objects.count(), 13)
		seed.run()
		self.assertEqual(Municipality.objects.count(), 13)
		self.assertEqual(str(Municipality.objects.get(hckey='tl-dl')), 'Dili')
		self.assertEqual(Municipality.objects.get(name='Oecusse').hckey, 'tl-am')

	def test_hckeys_match_the_map_features_exactly(self):
		"""hckey di database harus sama persis dengan hc-key pada data peta Highcharts, kalau tidak wilayah tidak berwarna."""
		geo = json.loads(Path(finders.find('main/charts/tl-all.geo.json')).read_text())
		map_keys = {f['properties']['hc-key'] for f in geo['features']}
		self.assertEqual(set(Municipality.objects.values_list('hckey', flat=True)), map_keys)

	def test_codes_are_short_and_unique(self):
		codes = list(Municipality.objects.values_list('code', flat=True))
		self.assertEqual(len(set(codes)), 13)
		self.assertTrue(all(c and len(c) <= 5 for c in codes))

	def test_api_requires_login_and_lists_all(self):
		self.assertEqual(self.client.get('/api/municipalities/').status_code, 401)
		self.client.force_login(User.objects.create_user('a@x.com'))
		names = [m['name'] for m in self.client.get('/api/municipalities/').json()['municipalities']]
		self.assertEqual(len(names), 13)
		self.assertEqual(names, sorted(names))


class StudentMunicipalityTests(TestCase):
	def setUp(self):
		seed.run()
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)
		self.dili = Municipality.objects.get(name='Dili')

	def test_set_change_and_clear(self):
		self.assertIsNone(self.client.get('/api/profile/').json()['municipality'])
		self.assertEqual(post(self.client, '/api/profile/', {'municipality': self.dili.pk}).json()['municipality'], self.dili.pk)
		self.user.refresh_from_db()
		self.assertEqual(self.user.municipality, self.dili)
		self.assertEqual(self.client.get('/api/me/').json()['municipality'], self.dili.pk)
		post(self.client, '/api/profile/', {'municipality': None})
		self.user.refresh_from_db()
		self.assertIsNone(self.user.municipality)

	def test_invalid_ids_rejected_and_name_untouched(self):
		self.user.name = 'Maria'
		self.user.save()
		for bad in ('abc', 99999, -1, {}, [1]):
			r = post(self.client, '/api/profile/', {'municipality': bad})
			self.assertEqual((r.status_code, r.json().get('error')), (400, 'municipality_invalid'), bad)
		self.user.refresh_from_db()
		self.assertEqual((self.user.name, self.user.municipality), ('Maria', None))

	def test_saving_only_name_keeps_municipality(self):
		post(self.client, '/api/profile/', {'municipality': self.dili.pk})
		post(self.client, '/api/profile/', {'name': 'Maria'})
		self.user.refresh_from_db()
		self.assertEqual((self.user.name, self.user.municipality), ('Maria', self.dili))

	def test_deleting_a_municipality_keeps_the_student(self):
		post(self.client, '/api/profile/', {'municipality': self.dili.pk})
		self.dili.delete()
		self.user.refresh_from_db()
		self.assertIsNone(self.user.municipality)

	def test_profile_and_home_pages_have_controls_without_personal_data(self):
		html = self.client.get('/profil/').content.decode()
		self.assertIn('id="municipality"', html)
		self.assertNotIn('Dili</option>', html, 'daftar diisi lewat API, bukan HTML (halaman bisa dicache)')
		self.assertIn('id="muni-cta"', self.client.get('/').content.decode())
