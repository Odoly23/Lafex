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


from .importer import parse_lines


class QuizImporterTests(TestCase):
	def test_parses_valid_lines(self):
		rows, errors = parse_lines('What is 1+1? | one | two | three | four | B | Rua.\nHello? | a | b | c | d | a', 'intermediate')
		self.assertEqual(errors, [])
		self.assertEqual((rows[0]['answer'], rows[0]['band'], rows[0]['explanation_tet']), ('b', 'intermediate', 'Rua.'))
		self.assertEqual(rows[1]['explanation_tet'], '')

	def test_rejects_bad_lines(self):
		rows, errors = parse_lines('too | few\nQ | a | b | c | d | e\nQ | a | b | | d | a\n' + 'Q' * 301 + ' | a | b | c | d | a')
		self.assertEqual(rows, [])
		self.assertEqual(len(errors), 4)


class QuizManageTests(TestCase):
	def setUp(self):
		seed.run()
		self.staff = User.objects.create_user('s@x.com', is_staff=True)
		self.student = User.objects.create_user('e@x.com')
		self.client.force_login(self.staff)

	def form(self, **over):
		d = {'question': 'New question?', 'choice_a': 'A1', 'choice_b': 'B1', 'choice_c': 'C1', 'choice_d': 'D1',
             'answer': 'c', 'explanation_tet': 'Tetun', 'band': 'advanced', 'active': 'on'}
		d.update(over)
		return d

	def test_roles(self):
		self.client.force_login(self.student)
		for url in ('/staff/quiz/', '/staff/quiz/novu/'):
			self.assertEqual(self.client.get(url).status_code, 403, url)
		self.assertEqual(self.client.post('/staff/quiz/import/', {'band': 'beginner', 'lines': 'x|a|b|c|d|a'}).status_code, 403)

	def test_create_edit_delete(self):
		self.assertEqual(self.client.post('/staff/quiz/novu/', self.form()).status_code, 302)
		q = QuizQuestion.objects.get(question='New question?')
		self.assertEqual((q.answer, q.band), ('c', 'advanced'))
		self.client.post(f'/staff/quiz/{q.pk}/edita/', self.form(answer='d'))
		q.refresh_from_db()
		self.assertEqual(q.answer, 'd')
		self.assertEqual(self.client.get(f'/staff/quiz/{q.pk}/hamoos/').status_code, 405)
		self.client.post(f'/staff/quiz/{q.pk}/hamoos/')
		self.assertFalse(QuizQuestion.objects.filter(pk=q.pk).exists())

	def test_invalid_answer_rejected(self):
		self.assertEqual(self.client.post('/staff/quiz/novu/', self.form(answer='e')).status_code, 200)
		self.assertFalse(QuizQuestion.objects.filter(question='New question?').exists())

	def test_import_and_update_by_question_text(self):
		n = QuizQuestion.objects.count()
		r = self.client.post('/staff/quiz/import/', {'band': 'advanced', 'lines': 'Imported Q? | a | b | c | d | b | Ok\nbad'}, follow=True)
		self.assertEqual(QuizQuestion.objects.count(), n + 1)
		self.assertContains(r, 'Liña 2')
		self.client.post('/staff/quiz/import/', {'band': 'advanced', 'lines': 'Imported Q? | a | b | c | d | c'})
		self.assertEqual(QuizQuestion.objects.count(), n + 1)
		self.assertEqual(QuizQuestion.objects.get(question='Imported Q?').answer, 'c')

	def test_deleted_question_does_not_break_old_attempts(self):
		from .models import QuizAttempt
		from django.utils import timezone
		ids = list(QuizQuestion.objects.values_list('pk', flat=True)[:3])
		attempt = QuizAttempt.objects.create(user=self.student, deadline=timezone.now() + timezone.timedelta(minutes=5), question_ids=ids, total=3)
		QuizQuestion.objects.filter(pk=ids[0]).delete()
		self.client.force_login(self.student)
		r = self.client.post(f'/api/quiz/{attempt.pk}/submit/', {'answers': {}}, content_type='application/json')
		self.assertEqual(r.status_code, 200)
		self.assertEqual(r.json()['total'], 2)
