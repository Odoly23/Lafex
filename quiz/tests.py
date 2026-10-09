from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from users.models import User

from . import seed
from .models import QuizAttempt, QuizQuestion


def post(client, url, data=None):
	return client.post(url, data or {}, content_type='application/json')


class QuizTests(TestCase):
	def setUp(self):
		seed.run()
		self.user = User.objects.create_user('a@x.com')
		self.client.force_login(self.user)

	def start(self):
		return post(self.client, '/api/quiz/start/').json()

	def answer_all(self, attempt, correct=True):
		answers = {}
		for q in attempt['questions']:
			right = QuizQuestion.objects.get(pk=q['id']).answer
			answers[str(q['id'])] = right if correct else ('a' if right != 'a' else 'b')
		return answers

	def test_requires_login(self):
		self.client.logout()
		self.assertEqual(post(self.client, '/api/quiz/start/').status_code, 401)

	def test_start_hides_answers_and_has_deadline(self):
		data = self.start()
		self.assertEqual(len(data['questions']), 10)
		self.assertEqual(data['seconds_left'], 300)
		for q in data['questions']:
			self.assertEqual(set(q), {'id', 'question', 'choices'})
			self.assertEqual(set(q['choices']), {'a', 'b', 'c', 'd'})
		a = QuizAttempt.objects.get(pk=data['attempt_id'])
		self.assertAlmostEqual((a.deadline - a.started_at).total_seconds(), 300, delta=2)

	def test_questions_match_student_band(self):
		beginner_ids = set(QuizQuestion.objects.filter(band='beginner').values_list('pk', flat=True))
		ids = {q['id'] for q in self.start()['questions']}
		self.assertEqual(len(ids), 10)
		self.assertTrue(beginner_ids <= ids, 'semua soal band siswa dipakai dulu; sisanya dilengkapi dari band lain')

	def test_no_questions(self):
		QuizQuestion.objects.update(active=False)
		self.assertEqual(post(self.client, '/api/quiz/start/').status_code, 404)

	def test_perfect_score_points(self):
		data = self.start()
		r = post(self.client, f"/api/quiz/{data['attempt_id']}/submit/", {'answers': self.answer_all(data)}).json()
		self.assertEqual((r['score'], r['total'], r['late'], r['points']), (10, 10, False, 10 * 2 + 5))
		self.user.refresh_from_db()
		self.assertEqual(self.user.points, 25)
		self.assertTrue(all(x['ok'] for x in r['review']))
		self.assertTrue(all(x['explanation_tet'] is not None for x in r['review']))

	def test_wrong_and_empty_answers(self):
		data = self.start()
		r = post(self.client, f"/api/quiz/{data['attempt_id']}/submit/", {'answers': self.answer_all(data, correct=False)}).json()
		self.assertEqual((r['score'], r['points']), (0, 0))
		data = self.start()
		r = post(self.client, f"/api/quiz/{data['attempt_id']}/submit/", {'answers': 'bukan dict'}).json()
		self.assertEqual(r['score'], 0)

	def test_late_submission_gets_no_points(self):
		data = self.start()
		QuizAttempt.objects.filter(pk=data['attempt_id']).update(deadline=timezone.now() - timedelta(minutes=1))
		r = post(self.client, f"/api/quiz/{data['attempt_id']}/submit/", {'answers': self.answer_all(data)}).json()
		self.assertEqual((r['late'], r['points']), (True, 0))
		self.assertEqual(r['score'], 10, 'nilai tetap dihitung, hanya poin yang tidak diberikan')

	def test_small_grace_after_deadline_is_accepted(self):
		data = self.start()
		QuizAttempt.objects.filter(pk=data['attempt_id']).update(deadline=timezone.now() - timedelta(seconds=5))
		r = post(self.client, f"/api/quiz/{data['attempt_id']}/submit/", {'answers': self.answer_all(data)}).json()
		self.assertFalse(r['late'])

	def test_cannot_submit_twice_or_for_someone_else(self):
		data = self.start()
		url = f"/api/quiz/{data['attempt_id']}/submit/"
		self.assertEqual(post(self.client, url, {'answers': {}}).status_code, 200)
		self.assertEqual(post(self.client, url, {'answers': self.answer_all(data)}).status_code, 409)
		data2 = self.start()
		self.client.force_login(User.objects.create_user('b@x.com'))
		self.assertEqual(post(self.client, f"/api/quiz/{data2['attempt_id']}/submit/", {'answers': {}}).status_code, 404)

	def test_perfect_bonus_needs_at_least_five_questions(self):
		QuizQuestion.objects.exclude(pk__in=list(QuizQuestion.objects.values_list('pk', flat=True)[:3])).update(active=False)
		data = self.start()
		self.assertEqual(len(data['questions']), 3)
		r = post(self.client, f"/api/quiz/{data['attempt_id']}/submit/", {'answers': self.answer_all(data)}).json()
		self.assertEqual(r['points'], 3 * 2)

	def test_page_renders(self):
		self.assertContains(self.client.get('/latihan/quiz/'), 'Quiz')
