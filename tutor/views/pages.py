from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie

from config.decorators import ALL_ROLES, allowed_users
from config.user_utils import user_group
from curriculum.models import Mission


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def MissionPage(request, slug):
	mission = get_object_or_404(Mission, slug=slug, active=True)
	context = {
        'group': user_group(request.user), 'page': 'mission', 'mission': mission,
        'title': mission.title_tet,
    }
	return render(request, 'tutor/mission.html', context)


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def ReviewPage(request):
	# Sengaja tanpa data pengguna di HTML: berkas ini dicache PWA dan data diambil lewat API / IndexedDB.
	context = {'group': user_group(request.user), 'page': 'review'}
	return render(request, 'tutor/review.html', context)
