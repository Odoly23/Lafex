from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from config.decorators import allowed_users
from config.user_utils import user_group
from pronounce.models import PronAttempt
from tutor.models import Session

from ..models import MonitorLog

ROLES = ['staff', 'admin']
LIST_LIMIT = 1000
NEEDS_HELP_BELOW = 60   # rata-rata di bawah ini = perlu dibantu
MIN_ATTEMPTS = 3        # minimal percobaan agar rata-rata dianggap berarti
RECENT_PER_STUDENT = 20


@login_required
@allowed_users(allowed_roles=ROLES)
def ChatList(request):
	objects = (Session.objects.select_related('user', 'mission')
               .annotate(n_turns=Count('turns', filter=Q(turns__role='user')))
               .filter(n_turns__gt=0).order_by('-started_at')[:LIST_LIMIT])
	context = {
        'group': user_group(request.user), 'page': 'monchat', 'objects': objects,
        'title': 'Chat estudante', 'legend': 'Chat estudante ho Maun Lafaek',
    }
	return render(request, 'report/chat_list.html', context)


@login_required
@allowed_users(allowed_roles=ROLES)
def ChatDetail(request, pk):
	session = get_object_or_404(Session.objects.select_related('user', 'mission'), pk=pk)
	MonitorLog.objects.create(viewer=request.user, session=session)  # audit
	context = {
        'group': user_group(request.user), 'page': 'monchat', 'session': session,
        'turns': session.turns.all(),
        'title': 'Chat estudante', 'legend': f'Chat: {session.user.email} · {session.mission.title_en}',
    }
	return render(request, 'report/chat_detail.html', context)


@login_required
@allowed_users(allowed_roles=ROLES)
def PronList(request):
	"""Estudante dengan rata-rata pontu pronunciation terendah (dari {RECENT_PER_STUDENT} percobaan terakhir)."""
	since = timezone.now() - timedelta(days=90)
	rows = (PronAttempt.objects.filter(created_at__gte=since, user__groups__name='estudante')
            .order_by('user_id', '-created_at').values_list('user_id', 'user__email', 'user__level', 'score', 'created_at'))
	per_user = {}
	for uid, email, level, score, at in rows:
		rec = per_user.setdefault(uid, {'email': email, 'level': level, 'scores': [], 'last': at, 'total': 0})
		rec['total'] += 1
		if len(rec['scores']) < RECENT_PER_STUDENT:
			rec['scores'].append(score)
	objects = []
	for rec in per_user.values():
		avg = round(sum(rec['scores']) / len(rec['scores']))
		objects.append({**rec, 'avg': avg, 'n': len(rec['scores']),
                        'needs_help': avg < NEEDS_HELP_BELOW and len(rec['scores']) >= MIN_ATTEMPTS})
	objects.sort(key=lambda r: (r['avg'], r['email']))
	context = {
        'group': user_group(request.user), 'page': 'monpron', 'objects': objects,
        'threshold': NEEDS_HELP_BELOW, 'min_attempts': MIN_ATTEMPTS,
        'title': 'Pronunciation', 'legend': 'Pontu pronunciation ki\'ik liu',
    }
	return render(request, 'report/pron_list.html', context)
