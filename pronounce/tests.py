from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from users.models import User

from . import scoring, seed
from .models import PronAttempt, PronPhrase


def post(client, url, data=None):
	return client.post(url, data or {}, content_type='application/json')


class ScoringTests(SimpleTestCase):
	def test_perfect_ignores_case_and_punctuation(self):
		r = scoring.score_phrase('Good morning, my name is Maria.', 'good morning my name is maria')
		self.assertEqual(r['score'], 100)
		self.assertEqual({d['status'] for d in r['detail']}, {'ok'})

	def test_nothing_heard(self):
		for heard in ('', None, '   '):
			r = scoring.score_phrase('How much is this?', heard)
			self.assertEqual(r['score'], 0)
			self.assertEqual({d['status'] for d in r['detail']}, {'missed'})

	def test_missing_word_is_marked(self):
		r = scoring.score_phrase('I live in Dili', 'I live Dili')
		self.assertEqual(r['score'], 75)
		self.assertEqual([d['status'] for d in r['detail']], ['ok', 'ok', 'missed', 'ok'])

	def test_close_word_gets_partial_credit_and_wrong_word_none(self):
		close = scoring.score_phrase('I like fish', 'I like fishes')
		self.assertEqual([d['status'] for d in close['detail']], ['ok', 'ok', 'close'])
		self.assertEqual(close['score'], round(100 * (2 + 0.6) / 3))
		wrong = scoring.score_phrase('I like fish', 'I like tea')
		self.assertEqual([d['status'] for d in wrong['detail']], ['ok', 'ok', 'missed'])

	def test_extra_words_lower_score_but_not_below_floor(self):
		base = scoring.score_phrase('Thank you', 'thank you')['score']
		extra = scoring.score_phrase('Thank you', 'thank you very very very very much')['score']
		self.assertEqual(base, 100)
		self.assertEqual(extra, 70)

	def test_confidence_scales_score(self):
		hi = scoring.score_phrase('Thank you', 'thank you', 1.0)['score']
		lo = scoring.score_phrase('Thank you', 'thank you', 0.0)['score']
		self.assertEqual((hi, lo), (100, 75))
		self.assertEqual(scoring.score_phrase('Thank you', 'thank you', 5)['score'], 100)
		self.assertEqual(scoring.score_phrase('Thank you', 'thank you', 'abc')['score'], 100)

	def test_apostrophes_and_empty_expected(self):
		self.assertEqual(scoring.score_phrase("I don't know", "i don’t know")['score'], 100)
		self.assertEqual(scoring.score_phrase('', 'anything')['score'], 0)


class PronApiTests(TestCase):
	def setUp(self):
		seed.run()
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)

	def test_requires_login(self):
		self.client.logout()
		self.assertEqual(post(self.client, '/api/pron/start/').status_code, 401)

	def test_start_returns_five_phrases_for_band(self):
		phrases = post(self.client, '/api/pron/start/').json()['phrases']
		self.assertEqual(len(phrases), 5)
		beginner = set(PronPhrase.objects.filter(band='beginner').values_list('pk', flat=True))
		self.assertTrue({p['id'] for p in phrases} <= beginner)

	def test_no_phrases(self):
		PronPhrase.objects.update(active=False)
		self.assertEqual(post(self.client, '/api/pron/start/').status_code, 404)

	def test_score_is_stored_and_points_only_first_attempt_per_day(self):
		ph = PronPhrase.objects.get(text_en='Thank you very much.')
		r1 = post(self.client, '/api/pron/score/', {'phrase_id': ph.pk, 'transcript': 'thank you very much', 'confidence': 0.9}).json()
		self.assertEqual(r1['score'], round(100 * (0.75 + 0.25 * 0.9)))
		self.assertEqual(r1['points'], r1['score'] // 10)
		r2 = post(self.client, '/api/pron/score/', {'phrase_id': ph.pk, 'transcript': 'thank you very much'}).json()
		self.assertEqual((r2['score'], r2['points']), (100, 0), 'tidak bisa menumpuk poin dengan mengulang kalimat yang sama')
		self.assertEqual(PronAttempt.objects.filter(user=self.user).count(), 2)
		self.user.refresh_from_db()
		self.assertEqual(self.user.points, r1['points'])

	def test_previous_day_attempt_does_not_block_points(self):
		ph = PronPhrase.objects.first()
		old = PronAttempt.objects.create(user=self.user, phrase=ph, score=50)
		PronAttempt.objects.filter(pk=old.pk).update(created_at=timezone.now() - timezone.timedelta(days=2))
		r = post(self.client, '/api/pron/score/', {'phrase_id': ph.pk, 'transcript': ph.text_en}).json()
		self.assertGreater(r['points'], 0)

	def test_bad_input(self):
		ph = PronPhrase.objects.first()
		for bad in (None, 'x', 99999, -3):
			self.assertEqual(post(self.client, '/api/pron/score/', {'phrase_id': bad, 'transcript': 'x'}).status_code, 404, bad)
		r = post(self.client, '/api/pron/score/', {'phrase_id': ph.pk, 'transcript': 'x' * 5000, 'confidence': True})
		self.assertEqual(r.status_code, 200)
		self.assertIsNone(PronAttempt.objects.latest('created_at').confidence, 'boolean bukan angka konfiansa')

	def test_page_renders(self):
		self.assertContains(self.client.get('/latihan/pronunciation/'), 'pronunciation')
