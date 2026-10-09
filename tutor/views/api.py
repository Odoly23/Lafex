from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from config.decorators import ALL_ROLES, api_allowed_users
from config.utils import json_body
from users.models import LEVELS
from billing import services as billing
from curriculum.models import Mission

from .. import ai
from ..models import Session, Turn

MAX_TEXT = 600
REVIEW_LIMIT = 50


def _quota_error(user):
	return JsonResponse({'error': 'daily_limit' if billing.is_active(user) else 'no_access',
                         'turns_left': billing.turns_left(user)}, status=402)


def _turn_json(r):
	return {k: r[k] for k in ('reply', 'correction', 'explanation', 'goal_met')}


def _progress(session):
	done = session.turns.filter(role='user').count()
	return {'student_turns': done, 'max_turns': session.mission.max_turns}


@require_POST
@api_allowed_users(ALL_ROLES)
def start(request):
	mission = get_object_or_404(Mission, slug=str(json_body(request).get('mission', '')), active=True)
	user = request.user
	if not billing.consume_turn(user):
		return _quota_error(user)
	session = Session.objects.create(user=user, mission=mission, level_start=user.level)
	try:
		r = ai.next_turn(session, '')
	except ai.TutorError as e:
		billing.refund_turn(user)
		session.delete()
		return JsonResponse({'error': 'refused' if isinstance(e, ai.TutorRefused) else 'tutor_failed'}, status=502)
	Turn.objects.create(session=session, idx=0, role='assistant', text=r['reply'])
	return JsonResponse({'session_id': session.id, 'turn': _turn_json(r), 'turns_left': billing.turns_left(user),
                         'mission': {'slug': mission.slug, 'title_tet': mission.title_tet, 'goal_tet': mission.goal_tet,
                                     'is_placement': mission.is_placement},
                         **_progress(session)})


@require_POST
@api_allowed_users(ALL_ROLES)
def turn(request, session_id):
	user = request.user
	session = get_object_or_404(Session.objects.select_related('mission'), pk=session_id, user=user)
	if session.finished_at:
		return JsonResponse({'error': 'finished'}, status=409)
	text = str(json_body(request).get('text', '')).strip()[:MAX_TEXT]
	if not text:
		return JsonResponse({'error': 'text_empty'}, status=400)
	if session.turns.filter(role='user').count() >= session.mission.max_turns:
		return JsonResponse({'error': 'mission_full'}, status=409)
	if not billing.consume_turn(user):
		return _quota_error(user)
	try:
		r = ai.next_turn(session, text)
	except ai.TutorError as e:
		billing.refund_turn(user)
		return JsonResponse({'error': 'refused' if isinstance(e, ai.TutorRefused) else 'tutor_failed'}, status=502)
	try:
		with transaction.atomic():
			idx = session.turns.count()
			Turn.objects.create(session=session, idx=idx, role='user', text=text,
                                correction=r['correction'], explanation=r['explanation'])
			Turn.objects.create(session=session, idx=idx + 1, role='assistant', text=r['reply'])
	except IntegrityError:  # dua permintaan bersamaan pada sesi yang sama
		billing.refund_turn(user)
		return JsonResponse({'error': 'busy'}, status=409)
	p = _progress(session)
	return JsonResponse({'turn': _turn_json(r), 'turns_left': billing.turns_left(user),
                         'can_finish': True, 'done': r['goal_met'] or p['student_turns'] >= p['max_turns'], **p})


def _promote(user, session, summary):
	"""Placement menetapkan level. Misi lain hanya menaikkan satu tingkat bila nilai >= 70."""
	cur = LEVELS.index(user.level)
	est = LEVELS.index(summary['level'])
	if session.mission.is_placement:
		user.level, user.placement_done = LEVELS[est], True
	elif est > cur and summary['score'] >= 70:
		user.level = LEVELS[cur + 1]
	else:
		return
	user.save(update_fields=['level', 'placement_done'])


@require_POST
@api_allowed_users(ALL_ROLES)
def finish(request, session_id):
	user = request.user
	session = get_object_or_404(Session.objects.select_related('mission'), pk=session_id, user=user)
	if not session.finished_at:
		if not session.turns.filter(role='user').exists():
			return JsonResponse({'error': 'no_turns'}, status=400)
		try:
			summary = ai.summarize(session)
		except ai.TutorError:
			return JsonResponse({'error': 'tutor_failed'}, status=502)
		with transaction.atomic():
			fresh = Session.objects.select_for_update().get(pk=session.pk)
			if not fresh.finished_at:  # penyelesaian ganda dari dua permintaan: yang pertama menang
				fresh.finished_at, fresh.score = timezone.now(), summary['score']
				fresh.level_end, fresh.summary = summary['level'], summary
				fresh.save()
				_promote(user, fresh, summary)
			session = fresh
	return JsonResponse({'summary': session.summary, 'score': session.score, 'level': user.level,
                         'placement_done': user.placement_done, 'is_placement': session.mission.is_placement})


@require_GET
@api_allowed_users(ALL_ROLES)
def review(request):
	"""Hanya untuk paket aktif. Klien menyimpan hasilnya di perangkat untuk dibuka offline."""
	user = request.user
	exp = billing.expires_at(user)
	if not (exp and exp > timezone.now()):
		return JsonResponse({'error': 'no_access'}, status=402)
	sessions = (Session.objects.filter(user=user, finished_at__isnull=False, mission__is_placement=False)
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
	return JsonResponse({'expires_at': exp.isoformat(), 'generated_at': timezone.now().isoformat(), 'sessions': out})
