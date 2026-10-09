from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, IntegerField, Q, When
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from config.decorators import allowed_users
from config.user_utils import user_group

from .forms import MissionForm
from .models import Mission


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def MissionList(request):
	objects = (Mission.objects.select_related('scenario')
               .annotate(n_sesaun=Count('session', filter=Q(session__finished_at__isnull=False)))
               .annotate(band_rank=Case(When(band='beginner', then=0), When(band='intermediate', then=1), default=2,
                                        output_field=IntegerField()))  # urut menurut kesulitan, bukan abjad
               .order_by('scenario__order', 'band_rank', 'order'))  # eksplisit: Meta.ordering diabaikan pada query annotate
	context = {
        'group': user_group(request.user), 'page': 'misaun', 'objects': objects,
        'title': 'Lista Misaun', 'legend': 'Lista Misaun',
    }
	return render(request, 'curriculum/list.html', context)


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def MaterialHub(request):
	from quiz.models import QuizQuestion
	from vocab.models import VocabItem
	context = {
        'group': user_group(request.user), 'page': 'materi', 'title': 'Materia no vokabulario', 'legend': 'Materia no vokabulario',
        'counts': {'missions': Mission.objects.filter(active=True, is_placement=False, is_free=False).count(),
                   'vocab': VocabItem.objects.filter(active=True).count(),
                   'quiz': QuizQuestion.objects.filter(active=True).count()},
    }
	return render(request, 'curriculum/hub.html', context)


@login_required
@allowed_users(allowed_roles=['staff', 'admin'])
def MissionEdit(request, pk):
	mission = get_object_or_404(Mission, pk=pk)
	form = MissionForm(request.POST or None, instance=mission)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Misaun rai ona.')
		return redirect('mission_list')
	context = {
        'group': user_group(request.user), 'page': 'misaun', 'form': form, 'cancel_url': '/staff/misaun/',
        'title': 'Edita misaun', 'legend': f'Edita misaun: {mission.slug}',
        'intro': 'Papél AI no objetivu Inglés sai instrusaun ba Maun Lafaek. Hakerek ho Inglés.',
    }
	return render(request, 'main/form.html', context)
