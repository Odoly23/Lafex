from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from config.decorators import allowed_users
from config.user_utils import user_group


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def Dashboard(request):
	context = {
        'group': user_group(request.user), 'page': 'dashboard',
        'title': 'Painel', 'legend': 'Painel jerál',
    }
	return render(request, 'report/dash.html', context)
