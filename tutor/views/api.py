from datetime import timedelta

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response

from config.api import APIAll, body
from users.models import LEVELS
from billing import services as billing
from progress import services as progress
from progress.services import POINTS
from curriculum.models import Mission

from .. import ai
from ..models import GrammarCheck, Session, Turn

MAX_TEXT = 600
REVIEW_LIMIT = 50


def _quota_error(user):
	return Response({'error': 'daily_limit' if billing.has_access(user) else 'no_access',
                         'turns_left': billing.turns_left(user)}, status=402)


def _turn_json(r):
	return {k: r[k] for k in ('reply', 'correction', 'explanation', 'goal_met')}


def _progress(session):
	done = session.turns.filter(role='user').count()
	return {'student_turns': done, 'max_turns': session.mission.max_turns}


class APIStart(APIAll):
	def post(self, request, format=None):
		mission = get_object_or_404(Mission, slug=str(body(request).get('mission', '')), active=True)
		user = request.user
		if not billing.consume_turn(user):
			return _quota_error(user)
		session = Session.objects.create(user=user, mission=mission, level_start=user.level)
		try:
			r = ai.next_turn(session, '')
		except ai.TutorError as e:
			billing.refund_turn(user)
			session.delete()
			return Response({'error': 'refused' if isinstance(e, ai.TutorRefused) else 'tutor_failed'}, status=502)
		Turn.objects.create(session=session, idx=0, role='assistant', text=r['reply'])
		return Response({'session_id': session.id, 'turn': _turn_json(r), 'turns_left': billing.turns_left(user),
                             'mission': {'slug': mission.slug, 'title_tet': mission.title_tet, 'goal_tet': mission.goal_tet,
                                         'is_placement': mission.is_placement},
                             **_progress(session)})


class APITurn(APIAll):
	def post(self, request, session_id, format=None):
		user = request.user
		session = get_object_or_404(Session.objects.select_related('mission'), pk=session_id, user=user)
		if session.finished_at:
			return Response({'error': 'finished'}, status=409)
		text = str(body(request).get('text', '')).strip()[:MAX_TEXT]
		if not text:
			return Response({'error': 'text_empty'}, status=400)
		if session.turns.filter(role='user').count() >= session.mission.max_turns:
			return Response({'error': 'mission_full'}, status=409)
		if not billing.consume_turn(user):
			return _quota_error(user)
		try:
			r = ai.next_turn(session, text)
		except ai.TutorError as e:
			billing.refund_turn(user)
			return Response({'error': 'refused' if isinstance(e, ai.TutorRefused) else 'tutor_failed'}, status=502)
		try:
			with transaction.atomic():
				idx = session.turns.count()
				Turn.objects.create(session=session, idx=idx, role='user', text=text,
                                    correction=r['correction'], explanation=r['explanation'])
				Turn.objects.create(session=session, idx=idx + 1, role='assistant', text=r['reply'])
		except IntegrityError:  # dua permintaan bersamaan pada sesi yang sama
			billing.refund_turn(user)
			return Response({'error': 'busy'}, status=409)
		p = _progress(session)
		return Response({'turn': _turn_json(r), 'turns_left': billing.turns_left(user),
                             'can_finish': True, 'done': r['goal_met'] or p['student_turns'] >= p['max_turns'], **p})


def _promote(user, session, summary):
	"""Placement menetapkan level. Misi lain hanya menaikkan satu tingkat bila nilai >= 70."""
	cur = LEVELS.index(user.level)
	est = LEVELS.index(summary['level'])
	if session.mission.is_placement:
		user.level, user.placement_done = LEVELS[est], True
		promoted = False  # level dari tes penempatan bukan prestasi belajar: tanpa sertifikat
	elif est > cur and summary['score'] >= 70 and not session.mission.is_free:
		user.level = LEVELS[cur + 1]
		promoted = True
	else:
		return False
	user.save(update_fields=['level', 'placement_done'])
	if promoted:
		progress.issue_certificate(user, user.level)
	return promoted


class APIFinish(APIAll):
	def post(self, request, session_id, format=None):
		user = request.user
		session = get_object_or_404(Session.objects.select_related('mission'), pk=session_id, user=user)
		new_cert = None
		if not session.finished_at:
			if not session.turns.filter(role='user').exists():
				return Response({'error': 'no_turns'}, status=400)
			try:
				summary = ai.summarize(session)
			except ai.TutorError:
				return Response({'error': 'tutor_failed'}, status=502)
			with transaction.atomic():
				fresh = Session.objects.select_for_update().get(pk=session.pk)
				if not fresh.finished_at:  # penyelesaian ganda dari dua permintaan: yang pertama menang
					fresh.finished_at, fresh.score = timezone.now(), summary['score']
					fresh.level_end, fresh.summary = summary['level'], summary
					fresh.save()
					if _promote(user, fresh, summary):
						new_cert = user.certificates.filter(level=user.level).values_list('code', flat=True).first()
					m = fresh.mission
					if m.is_free:
						progress.award(user, 'chat', POINTS['chat_finish'] + summary['score'] // 20, ref=fresh.pk)
					elif m.is_placement:
						progress.award(user, 'situasaun', 0, ref=fresh.pk)
					else:
						progress.award(user, 'situasaun', POINTS['situasaun_finish'] + summary['score'] // 10, ref=fresh.pk)
				session = fresh
		return Response({'summary': session.summary, 'score': session.score, 'level': user.level,
                             'placement_done': user.placement_done, 'is_placement': session.mission.is_placement,
                         'new_certificate': new_cert, 'points': user.points, 'streak': progress.current_streak(user)})


class APIReview(APIAll):
	def get(self, request, format=None):
		"""Hanya untuk paket aktif. Klien menyimpan hasilnya di perangkat untuk dibuka offline."""
		user = request.user
		if not billing.has_access(user):
			return Response({'error': 'no_access'}, status=402)
		exp = billing.expires_at(user)
		if not (exp and exp > timezone.now()):  # mode gratis: tanpa paket, kunci offline diperbarui tiap kali online
			exp = timezone.now() + timedelta(days=7)
		sessions = (Session.objects.filter(user=user, finished_at__isnull=False, mission__is_placement=False, mission__is_free=False)
                    .select_related('mission__scenario').prefetch_related('turns')[:REVIEW_LIMIT])
		out = []
		for s in sessions:
			m = s.mission
			out.append({
                'id': s.id, 'finished_at': s.finished_at.isoformat(), 'score': s.score, 'level': s.level_end,
                'mission': {'slug': m.slug, 'title_tet': m.title_tet, 'title_en': m.title_en,
                            'scenario_tet': m.scenario.title_tet if m.scenario else ''},
                'summary': s.summary,
                'turns': [{'role': t.role, 'text': t.text, 'correction': t.correction, 'explanation': t.explanation}
                          for t in s.turns.all()],
            })
		return Response({'expires_at': exp.isoformat(), 'generated_at': timezone.now().isoformat(), 'sessions': out})


class APIGrammar(APIAll):
	"""Grammar Fix: siswa menulis kalimat, Maun Lafaek mengoreksi (memakai satu jatah giliran)."""
	def post(self, request, format=None):
		user = request.user
		text = str(body(request).get('text', '')).strip()[:MAX_TEXT]
		if len(text) < 2:
			return Response({'error': 'text_empty'}, status=400)
		if not billing.consume_turn(user):
			return _quota_error(user)
		try:
			r = ai.fix_grammar(text, user.level)
		except ai.TutorError as e:
			billing.refund_turn(user)
			return Response({'error': 'refused' if isinstance(e, ai.TutorRefused) else 'tutor_failed'}, status=502)
		GrammarCheck.objects.create(user=user, original=text, corrected=r['corrected'], ok=r['ok'], result=r)
		pts = POINTS['grammar'] + (POINTS['grammar_perfect'] if r['ok'] else 0)
		progress.award(user, 'grammar', pts)
		return Response({**r, 'points': pts, 'turns_left': billing.turns_left(user)})
