from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from config.decorators import allowed_users
from config.user_utils import user_group

from billing import services as billing

from .forms import StudentForm
from .models import User


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def StudentList(request):
	objects = (User.objects.filter(groups__name='estudante')
               .select_related('entitlement', 'municipality')
               .annotate(n_sesaun=Count('sessions', filter=Q(sessions__finished_at__isnull=False)))
               .order_by('-date_joined'))
	context = {
        'group': user_group(request.user), 'page': 'siswa', 'objects': objects,
        'title': 'Lista Estudante', 'legend': 'Lista Estudante',
    }
	return render(request, 'users/list.html', context)


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def StudentEdit(request, pk):
	# Hanya estudante yang bisa diedit di sini (staff/admin dikelola lewat Django admin).
	student = get_object_or_404(User, pk=pk, groups__name='estudante')
	group = user_group(request.user)
	form = StudentForm(request.POST or None, instance=student, can_grant=(group == 'admin'))
	if request.method == 'POST' and form.is_valid():
		form.save()
		plan = form.cleaned_data.get('grant_plan')
		if plan:
			billing.grant_plan(student, plan)
		messages.success(request, 'Dadus estudante rai ona.')
		return redirect('student_list')
	context = {
        'group': group, 'page': 'siswa', 'form': form, 'cancel_url': '/staff/siswa/',
        'title': 'Edita estudante', 'legend': f'Edita estudante: {student.email}',
        'intro': f'Nível, naran no estatutu. Email la bele ubah. Pontu: {student.points}.',
    }
	return render(request, 'main/form.html', context)
