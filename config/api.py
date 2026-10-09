from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler as drf_exception_handler

from .auth import SessionAuth401


class HasRole(BasePermission):
	roles = []

	def has_permission(self, request, view):
		u = request.user
		return bool(u and u.is_authenticated and (
            u.is_superuser or u.groups.filter(name__in=self.roles).exists()))


class IsAnyRole(HasRole):
	roles = ['estudante', 'staff', 'admin']


class IsStaffRole(HasRole):
	roles = ['staff', 'admin']


class IsAdminRole(HasRole):
	roles = ['admin']


class APIAll(APIView):
	"""Untuk semua peran yang masuk (siswa, staff, admin)."""
	authentication_classes = [SessionAuth401]
	permission_classes = [IsAnyRole]


class APIStaff(APIView):
	authentication_classes = [SessionAuth401]
	permission_classes = [IsStaffRole]


class APIAdmin(APIView):
	authentication_classes = [SessionAuth401]
	permission_classes = [IsAdminRole]


def body(request):
	"""Isi JSON sebagai dict ({} bila bukan objek)."""
	return request.data if isinstance(request.data, dict) else {}


def exception_handler(exc, context):
	"""Bentuk galat seragam {'error': kode}, sama dengan yang dibaca JavaScript."""
	response = drf_exception_handler(exc, context)
	if response is not None and isinstance(response.data, dict) and 'detail' in response.data:
		names = {400: 'bad_request', 401: 'unauthorized', 403: 'forbidden', 404: 'not_found',
                 405: 'method_not_allowed', 415: 'bad_request', 429: 'throttled'}
		response.data = {'error': names.get(response.status_code, 'error')}
	return response
