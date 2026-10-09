from django.db.models import Max
from rest_framework.response import Response

from config.api import APIAll
from tutor.models import Session

from .models import Scenario


class APICurriculum(APIAll):
	def get(self, request, format=None):
		best = dict(Session.objects.filter(user=request.user, finished_at__isnull=False)
                    .values_list('mission_id').annotate(b=Max('score')))
		out = []
		for sc in Scenario.objects.filter(active=True).prefetch_related('missions'):
			out.append({
                'slug': sc.slug, 'title_tet': sc.title_tet, 'emoji': sc.emoji,
                'missions': [{'slug': m.slug, 'band': m.band, 'title_tet': m.title_tet, 'goal_tet': m.goal_tet,
                              'best_score': best.get(m.id)}
                             for m in sc.missions.all() if m.active and not m.is_placement],
            })
		return Response({'scenarios': out})
