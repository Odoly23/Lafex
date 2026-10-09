from django.test import TestCase

from users.models import User

from . import seed
from .models import UserVocab, VocabCategory, VocabItem


def post(client, url, data=None):
	return client.post(url, data or {}, content_type='application/json')


class VocabTests(TestCase):
	def setUp(self):
		seed.run()
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)

	def test_seed_is_idempotent_and_complete(self):
		before = VocabItem.objects.count()
		seed.run()
		self.assertEqual(VocabItem.objects.count(), before)
		self.assertEqual(set(VocabCategory.objects.values_list('slug', flat=True)), {'eskola', 'merkadu', 'kantor'})
		self.assertEqual(VocabItem.objects.filter(category__slug='eskola').count(), 10)

	def test_requires_login(self):
		self.client.logout()
		self.assertEqual(self.client.get('/api/vocab/').status_code, 401)
		self.assertEqual(self.client.get('/belajar/kosakata/').status_code, 302)

	def test_categories_with_progress(self):
		item = VocabItem.objects.filter(category__slug='eskola').first()
		post(self.client, '/api/vocab/known/', {'item_id': item.pk, 'known': True})
		cats = {c['slug']: c for c in self.client.get('/api/vocab/').json()['categories']}
		self.assertEqual((cats['eskola']['total'], cats['eskola']['known']), (10, 1))
		self.assertEqual(cats['merkadu']['known'], 0)

	def test_inactive_items_and_categories_are_hidden(self):
		VocabItem.objects.filter(en='school').update(active=False)
		data = self.client.get('/api/vocab/eskola/').json()
		self.assertEqual(len(data['items']), 9)
		VocabCategory.objects.filter(slug='kantor').update(active=False)
		self.assertEqual(self.client.get('/api/vocab/kantor/').status_code, 404)
		self.assertEqual(self.client.get('/belajar/kosakata/kantor/').status_code, 404)
		self.assertNotIn('kantor', [c['slug'] for c in self.client.get('/api/vocab/').json()['categories']])

	def test_points_only_once_per_word(self):
		item = VocabItem.objects.first()
		self.assertEqual(post(self.client, '/api/vocab/known/', {'item_id': item.pk, 'known': True}).json()['points'], 1)
		post(self.client, '/api/vocab/known/', {'item_id': item.pk, 'known': False})
		again = post(self.client, '/api/vocab/known/', {'item_id': item.pk, 'known': True}).json()
		self.assertEqual(again['points'], 0, 'tidak bisa mengumpulkan poin dengan menandai ulang')
		self.user.refresh_from_db()
		self.assertEqual(self.user.points, 1)
		self.assertEqual(UserVocab.objects.filter(user=self.user).count(), 1)

	def test_invalid_item_ids(self):
		for bad in (None, 'abc', 999999, -1, {}):
			self.assertEqual(post(self.client, '/api/vocab/known/', {'item_id': bad, 'known': True}).status_code, 404, bad)

	def test_progress_is_per_user(self):
		item = VocabItem.objects.first()
		post(self.client, '/api/vocab/known/', {'item_id': item.pk, 'known': True})
		other = User.objects.create_user('b@x.com')
		self.client.force_login(other)
		items = self.client.get(f'/api/vocab/{item.category.slug}/').json()['items']
		self.assertFalse(any(i['known'] for i in items))

	def test_pages_render(self):
		self.assertContains(self.client.get('/belajar/kosakata/'), 'Kosa kata')
		self.assertContains(self.client.get('/belajar/kosakata/merkadu/'), 'Merkadu')
