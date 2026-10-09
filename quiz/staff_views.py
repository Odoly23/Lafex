from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.decorators import allowed_users
from config.user_utils import user_group

from .forms import ImportForm, QuestionForm
from .importer import parse_lines
from .models import QuizQuestion

ROLES = ['staff', 'admin']


def _ctx(request, **extra):
	return {'group': user_group(request.user), 'page': 'quizsoal', **extra}


@login_required
@allowed_users(allowed_roles=ROLES)
def QuestionList(request):
	return render(request, 'quiz/staff_list.html', _ctx(
        request, objects=QuizQuestion.objects.all(), import_form=ImportForm(), title='Pergunta quiz', legend='Pergunta quiz'))


@login_required
@allowed_users(allowed_roles=ROLES)
def QuestionEdit(request, pk=None):
	obj = get_object_or_404(QuizQuestion, pk=pk) if pk else None
	form = QuestionForm(request.POST or None, instance=obj)
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, 'Pergunta rai ona.')
		return redirect('quiz_questions')
	legend = 'Edita pergunta' if obj else 'Pergunta foun'
	return render(request, 'main/form.html', _ctx(request, form=form, cancel_url='/staff/quiz/', title=legend, legend=legend,
                                                  intro='Pergunta no opsaun hakerek ho Inglés; esplikasaun ho Tetun.'))


@require_POST
@login_required
@allowed_users(allowed_roles=ROLES)
def QuestionDelete(request, pk):
	get_object_or_404(QuizQuestion, pk=pk).delete()
	messages.success(request, 'Pergunta hamoos ona.')
	return redirect('quiz_questions')


@require_POST
@login_required
@allowed_users(allowed_roles=ROLES)
def QuestionImport(request):
	form = ImportForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Hili band no tempel lista pergunta.')
		return redirect('quiz_questions')
	rows, errors = parse_lines(form.cleaned_data['lines'], form.cleaned_data['band'])
	for r in rows:
		QuizQuestion.objects.update_or_create(question=r['question'], defaults=r)
	if rows:
		messages.success(request, f'Import: {len(rows)} pergunta rai ona.')
	for e in errors[:10]:
		messages.warning(request, e)
	return redirect('quiz_questions')
