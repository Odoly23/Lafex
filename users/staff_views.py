from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render

from config.decorators import allowed_users
from config.user_utils import user_group

from .models import User


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def StudentList(request):
	objects = (User.objects.filter(groups__name='estudante')
               .select_related('entitlement')
               .annotate(n_sesaun=Count('sessions', filter=Q(sessions__finished_at__isnull=False)))
               .order_by('-date_joined'))
	context = {
        'group': user_group(request.user), 'page': 'siswa', 'objects': objects,
        'title': 'Lista Estudante', 'legend': 'Lista Estudante',
    }
	return render(request, 'users/list.html', context)
