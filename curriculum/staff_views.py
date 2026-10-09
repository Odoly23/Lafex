from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from config.decorators import allowed_users
from config.user_utils import user_group

from .models import Mission


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def MissionList(request):
	objects = (Mission.objects.select_related('scenario')
               .annotate(n_sesaun=Count('session', filter=Q(session__finished_at__isnull=False))))
	context = {
        'group': user_group(request.user), 'page': 'misaun', 'objects': objects,
        'title': 'Lista Misaun', 'legend': 'Lista Misaun',
    }
	return render(request, 'curriculum/list.html', context)
