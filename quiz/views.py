import random
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response

from config.api import APIAll, body
from config.decorators import ALL_ROLES, allowed_users
from config.user_utils import user_group
from curriculum.models import band_for_level
from progress import services as progress
from progress.services import POINTS

from .models import QuizAttempt, QuizQuestion

QUESTIONS_PER_QUIZ = 10
MINUTES = 5
GRACE_SECONDS = 20  # toleransi jaringan: jawaban masih diterima sedikit setelah batas waktu


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def QuizPage(request):
	context = {'group': user_group(request.user), 'page': 'quiz', 'title': 'Quiz', 'minutes': MINUTES, 'n': QUESTIONS_PER_QUIZ}
	return render(request, 'quiz/quiz.html', context)


def _pick(user):
	"""Soal sesuai band siswa; jika kurang, lengkapi dari band lain."""
	band = band_for_level(user.level)
	own = list(QuizQuestion.objects.filter(active=True, band=band))
	random.shuffle(own)
	picked = own[:QUESTIONS_PER_QUIZ]
	if len(picked) < QUESTIONS_PER_QUIZ:
		rest = list(QuizQuestion.objects.filter(active=True).exclude(pk__in=[q.pk for q in picked]))
		random.shuffle(rest)
		picked += rest[:QUESTIONS_PER_QUIZ - len(picked)]
	return picked


class APIQuizStart(APIAll):
	def post(self, request, format=None):
		questions = _pick(request.user)
		if not questions:
			return Response({'error': 'quiz_none'}, status=404)
		now = timezone.now()
		attempt = QuizAttempt.objects.create(
            user=request.user, deadline=now + timedelta(minutes=MINUTES),
            question_ids=[q.pk for q in questions], total=len(questions))
		return Response({
            'attempt_id': attempt.pk, 'seconds_left': MINUTES * 60,
            # Jawaban benar TIDAK dikirim ke klien.
            'questions': [{'id': q.pk, 'question': q.question, 'choices': q.choices()} for q in questions],
        })


class APIQuizSubmit(APIAll):
	def post(self, request, attempt_id, format=None):
		answers = body(request).get('answers')
		answers = answers if isinstance(answers, dict) else {}
		with transaction.atomic():
			attempt = get_object_or_404(QuizAttempt.objects.select_for_update(), pk=attempt_id, user=request.user)
			if attempt.finished_at:
				return Response({'error': 'finished'}, status=409)
			now = timezone.now()
			late = now > attempt.deadline + timedelta(seconds=GRACE_SECONDS)
			questions = {q.pk: q for q in QuizQuestion.objects.filter(pk__in=attempt.question_ids)}
			review, correct = [], 0
			for qid in attempt.question_ids:
				q = questions.get(qid)
				if not q:
					continue
				given = str(answers.get(str(qid), '')).lower()[:1]
				ok = given == q.answer
				correct += ok
				review.append({'id': qid, 'question': q.question, 'choices': q.choices(), 'given': given,
                               'answer': q.answer, 'ok': ok, 'explanation_tet': q.explanation_tet})
			attempt.answers = {str(k): str(v)[:1] for k, v in answers.items() if str(k).isdigit()}
			attempt.finished_at, attempt.score, attempt.late = now, correct, late
			attempt.save()
		points = 0
		if not late:
			points = correct * POINTS['quiz_correct'] + (POINTS['quiz_perfect'] if correct == len(review) >= 5 else 0)
		progress.award(request.user, 'quiz', points, ref=attempt.pk)
		return Response({'score': correct, 'total': len(review), 'late': late, 'points': points, 'review': review})
