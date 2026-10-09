from rest_framework.response import Response

from config.api import APIAll

from .models import Municipality


class APIMunicipalities(APIAll):
	def get(self, request, format=None):
		return Response({'municipalities': [{'id': m.pk, 'name': m.name} for m in Municipality.objects.all()]})
