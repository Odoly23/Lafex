from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response

from config.api import APIAll, body
from config.decorators import ALL_ROLES, allowed_users
from config.user_utils import user_group
from progress import services as progress
from progress.services import POINTS

from .models import UserVocab, VocabCategory, VocabItem


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def VocabCategories(request):
	context = {'group': user_group(request.user), 'page': 'kosakata', 'title': 'Kosa kata'}
	return render(request, 'vocab/categories.html', context)


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def VocabStudy(request, slug):
	cat = get_object_or_404(VocabCategory, slug=slug, active=True)
	context = {'group': user_group(request.user), 'page': 'kosakata', 'category': cat, 'title': cat.name_tet}
	return render(request, 'vocab/study.html', context)


class APIVocabCategories(APIAll):
	def get(self, request, format=None):
		known = dict(UserVocab.objects.filter(user=request.user, known=True, item__active=True)
                     .values_list('item__category_id').annotate(n=Count('id')))
		cats = (VocabCategory.objects.filter(active=True)
                .annotate(total=Count('items', filter=Q(items__active=True))))
		return Response({'categories': [
            {'slug': c.slug, 'name_tet': c.name_tet, 'name_en': c.name_en, 'emoji': c.emoji,
             'total': c.total, 'known': known.get(c.id, 0)} for c in cats]})


class APIVocabStudy(APIAll):
	def get(self, request, slug, format=None):
		cat = get_object_or_404(VocabCategory, slug=slug, active=True)
		items = list(cat.items.filter(active=True))
		known = set(UserVocab.objects.filter(user=request.user, item__in=items, known=True).values_list('item_id', flat=True))
		return Response({
            'category': {'slug': cat.slug, 'name_tet': cat.name_tet, 'name_en': cat.name_en},
            'items': [{'id': i.id, 'tet': i.tet, 'en': i.en, 'example_en': i.example_en, 'known': i.id in known}
                      for i in items],
        })


class APIVocabKnown(APIAll):
	"""Tandai kata sudah/belum dikuasai. Poin hanya diberikan sekali per kata (anti-curang)."""
	def post(self, request, format=None):
		data = body(request)
		item = get_object_or_404(VocabItem, pk=data.get('item_id') if str(data.get('item_id', '')).isdigit() else 0, active=True)
		known = bool(data.get('known'))
		uv, _ = UserVocab.objects.get_or_create(user=request.user, item=item)
		uv.known, uv.updated_at = known, timezone.now()
		pts = 0
		if known and not uv.rewarded:
			uv.rewarded = True
			pts = POINTS['vocab_known']
		uv.save()
		if pts:
			progress.award(request.user, 'vocab', pts, ref=item.pk)
		return Response({'known': uv.known, 'points': pts})
