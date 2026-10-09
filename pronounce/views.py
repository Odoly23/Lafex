import random
from datetime import datetime, time

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response

from config.api import APIAll, body
from config.decorators import ALL_ROLES, allowed_users
from config.user_utils import user_group
from curriculum.models import band_for_level
from progress import services as progress
from progress.services import POINTS

from . import scoring
from .models import PronAttempt, PronPhrase

PHRASES_PER_EXAM = 5


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def PronPage(request):
	context = {'group': user_group(request.user), 'page': 'pron', 'title': 'Pronunciation'}
	return render(request, 'pronounce/pron.html', context)


class APIPronStart(APIAll):
	def post(self, request, format=None):
		band = band_for_level(request.user.level)
		own = list(PronPhrase.objects.filter(active=True, band=band))
		random.shuffle(own)
		picked = own[:PHRASES_PER_EXAM]
		if len(picked) < PHRASES_PER_EXAM:
			rest = list(PronPhrase.objects.filter(active=True).exclude(pk__in=[p.pk for p in picked]))
			random.shuffle(rest)
			picked += rest[:PHRASES_PER_EXAM - len(picked)]
		if not picked:
			return Response({'error': 'pron_none'}, status=404)
		return Response({'phrases': [{'id': p.pk, 'text_en': p.text_en, 'text_tet': p.text_tet} for p in picked]})


class APIPronScore(APIAll):
	def post(self, request, format=None):
		data = body(request)
		phrase = get_object_or_404(PronPhrase, pk=data.get('phrase_id') if str(data.get('phrase_id', '')).isdigit() else 0, active=True)
		transcript = str(data.get('transcript', ''))[:300]
		conf = data.get('confidence')
		conf = float(conf) if isinstance(conf, (int, float)) and not isinstance(conf, bool) else None
		r = scoring.score_phrase(phrase.text_en, transcript, conf)
		# Awal hari ini (zona waktu Dili), dihitung di Python: tanpa fungsi tanggal database.
		day_start = timezone.make_aware(datetime.combine(timezone.localdate(), time.min))
		first_today = not PronAttempt.objects.filter(user=request.user, phrase=phrase, created_at__gte=day_start).exists()
		PronAttempt.objects.create(user=request.user, phrase=phrase, transcript=r['heard'], confidence=conf,
                                   score=r['score'], detail=r['detail'])
		points = r['score'] // POINTS['pron_divisor'] if first_today else 0  # poin hanya percobaan pertama per kalimat per hari
		progress.award(request.user, 'pron', points, ref=phrase.pk)
		return Response({'score': r['score'], 'detail': r['detail'], 'heard': r['heard'], 'points': points})
