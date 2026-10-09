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


from .importer import parse_lines


class ImporterTests(TestCase):
	def test_parses_separators_and_optional_example(self):
		rows, errors = parse_lines('livru ; book ; This is a book.\nmeza | table\nkadeira\tchair\n\n')
		self.assertEqual(rows, [('livru', 'book', 'This is a book.'), ('meza', 'table', ''), ('kadeira', 'chair', '')])
		self.assertEqual(errors, [])

	def test_reports_bad_lines_with_numbers(self):
		rows, errors = parse_lines('ok ; fine\njust one word\n ; empty\n' + 'x' * 100 + ' ; too long')
		self.assertEqual(rows, [('ok', 'fine', '')])
		self.assertEqual(len(errors), 3)
		self.assertIn('Liña 2', errors[0])

	def test_caps_line_count(self):
		rows, errors = parse_lines('\n'.join(f'a{i} ; b{i}' for i in range(250)))
		self.assertEqual(len(rows), 200)
		self.assertIn('200', errors[0])


class VocabManageTests(TestCase):
	def setUp(self):
		seed.run()
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.student = User.objects.create_user('e@x.com')
		self.cat = VocabCategory.objects.get(slug='eskola')
		self.client.force_login(self.staff)

	def test_roles(self):
		self.client.force_login(self.student)
		for url in ('/staff/kosakata/', f'/staff/kosakata/{self.cat.pk}/', '/staff/kosakata/kategoria/novu/'):
			self.assertEqual(self.client.get(url).status_code, 403, url)
		self.assertEqual(self.client.post(f'/staff/kosakata/{self.cat.pk}/import/', {'lines': 'a;b'}).status_code, 403)

	def test_category_create_and_unique_slug(self):
		r = self.client.post('/staff/kosakata/kategoria/novu/', {'slug': 'saude', 'name_tet': 'Saúde', 'name_en': 'Health',
                                                                 'emoji': '🏥', 'order': 4, 'active': 'on'})
		self.assertEqual(r.status_code, 302)
		self.assertTrue(VocabCategory.objects.filter(slug='saude').exists())
		again = self.client.post('/staff/kosakata/kategoria/novu/', {'slug': 'saude', 'name_tet': 'x', 'name_en': 'x', 'order': 1})
		self.assertEqual(again.status_code, 200)
		self.assertEqual(VocabCategory.objects.filter(slug='saude').count(), 1)

	def test_item_create_edit_delete(self):
		r = self.client.post(f'/staff/kosakata/{self.cat.pk}/item/novu/', {'tet': 'bola', 'en': 'ball', 'example_en': 'A ball.', 'order': 99, 'active': 'on'})
		self.assertEqual(r.status_code, 302)
		item = VocabItem.objects.get(en='ball')
		self.assertEqual(item.category, self.cat)
		self.client.post(f'/staff/kosakata/item/{item.pk}/edita/', {'tet': 'bola foun', 'en': 'ball', 'order': 99, 'active': 'on'})
		item.refresh_from_db()
		self.assertEqual(item.tet, 'bola foun')
		self.assertEqual(self.client.get(f'/staff/kosakata/item/{item.pk}/hamoos/').status_code, 405, 'hapus hanya lewat POST')
		self.assertTrue(VocabItem.objects.filter(pk=item.pk).exists())
		self.client.post(f'/staff/kosakata/item/{item.pk}/hamoos/')
		self.assertFalse(VocabItem.objects.filter(pk=item.pk).exists())

	def test_item_pages_render_and_unknown_category_404(self):
		self.assertContains(self.client.get(f'/staff/kosakata/{self.cat.pk}/'), 'Import lista')
		self.assertEqual(self.client.get('/staff/kosakata/99999/').status_code, 404)

	def test_import_adds_and_updates_without_duplicates(self):
		before = self.cat.items.count()
		r = self.client.post(f'/staff/kosakata/{self.cat.pk}/import/', {'lines': 'bola ; ball\nlivru foun ; BOOK ; New example.\nbad line'}, follow=True)
		self.assertEqual(self.cat.items.count(), before + 1, 'BOOK memperbarui "book" yang sudah ada (tanpa membedakan huruf besar)')
		self.assertEqual(self.cat.items.get(en='book').tet, 'livru foun')
		self.assertContains(r, 'Liña 3')
		self.assertContains(r, '1 foun, 1 atualiza')
		self.assertEqual(self.client.get(f'/staff/kosakata/{self.cat.pk}/import/').status_code, 405)

	def test_new_items_appear_for_students(self):
		self.client.post(f'/staff/kosakata/{self.cat.pk}/import/', {'lines': 'bola ; ball'})
		self.client.force_login(self.student)
		items = self.client.get('/api/vocab/eskola/').json()['items']
		self.assertIn('ball', [i['en'] for i in items])
