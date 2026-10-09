from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.decorators import allowed_users
from config.user_utils import user_group

from .forms import CategoryForm, ItemForm
from .importer import parse_lines
from .models import VocabCategory, VocabItem

ROLES = ['staff', 'admin']


def _ctx(request, **extra):
	return {'group': user_group(request.user), 'page': 'kosakatamaster', **extra}


@login_required
@allowed_users(allowed_roles=ROLES)
def CategoryList(request):
	objects = VocabCategory.objects.annotate(n_items=Count('items', filter=Q(items__active=True)))
	return render(request, 'vocab/staff_categories.html', _ctx(request, objects=objects, title='Kosa kata', legend='Kategoria kosa kata'))


@login_required
@allowed_users(allowed_roles=ROLES)
def CategoryEdit(request, pk=None):
	cat = get_object_or_404(VocabCategory, pk=pk) if pk else None
	form = CategoryForm(request.POST or None, instance=cat)
	if request.method == 'POST' and form.is_valid():
		saved = form.save()
		messages.success(request, 'Kategoria rai ona.')
		return redirect('vocab_items', pk=saved.pk)
	legend = f'Edita kategoria: {cat.name_tet}' if cat else 'Kategoria foun'
	return render(request, 'main/form.html', _ctx(request, form=form, cancel_url='/staff/kosakata/', title=legend, legend=legend))


@login_required
@allowed_users(allowed_roles=ROLES)
def ItemList(request, pk):
	cat = get_object_or_404(VocabCategory, pk=pk)
	return render(request, 'vocab/staff_items.html', _ctx(
        request, category=cat, objects=cat.items.all(), title=cat.name_tet, legend=f'{cat.emoji} {cat.name_tet} / {cat.name_en}'))


@login_required
@allowed_users(allowed_roles=ROLES)
def ItemEdit(request, pk=None, category_pk=None):
	item = get_object_or_404(VocabItem, pk=pk) if pk else None
	cat = item.category if item else get_object_or_404(VocabCategory, pk=category_pk)
	form = ItemForm(request.POST or None, instance=item)
	if request.method == 'POST' and form.is_valid():
		obj = form.save(commit=False)
		obj.category = cat
		obj.save()
		messages.success(request, 'Kosa kata rai ona.')
		return redirect('vocab_items', pk=cat.pk)
	legend = f'Edita kosa kata: {item.tet}' if item else f'Kosa kata foun ({cat.name_tet})'
	return render(request, 'main/form.html', _ctx(request, form=form, cancel_url=f'/staff/kosakata/{cat.pk}/', title=legend, legend=legend))


@require_POST
@login_required
@allowed_users(allowed_roles=ROLES)
def ItemDelete(request, pk):
	item = get_object_or_404(VocabItem, pk=pk)
	cat_pk = item.category_id
	item.delete()
	messages.success(request, 'Kosa kata hamoos ona.')
	return redirect('vocab_items', pk=cat_pk)


@require_POST
@login_required
@allowed_users(allowed_roles=ROLES)
def ItemImport(request, pk):
	cat = get_object_or_404(VocabCategory, pk=pk)
	rows, errors = parse_lines(request.POST.get('lines', ''))
	existing = {i.en.lower(): i for i in cat.items.all()}
	added = updated = 0
	for order, (tet, en, ex) in enumerate(rows, cat.items.count() + 1):
		item = existing.get(en.lower())
		if item:
			item.tet, item.example_en = tet, ex or item.example_en
			item.save()
			updated += 1
		else:
			existing[en.lower()] = VocabItem.objects.create(category=cat, tet=tet, en=en, example_en=ex, order=order)
			added += 1
	if rows:
		messages.success(request, f'Import: {added} foun, {updated} atualiza.')
	for e in errors[:10]:
		messages.warning(request, e)
	return redirect('vocab_items', pk=cat.pk)
