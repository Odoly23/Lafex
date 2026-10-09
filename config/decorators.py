from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect, render

# Peran (Django Groups). Pengguna biasa = student; staff = pengelola materi; admin = penuh.
ALL_ROLES = ['student', 'staff', 'admin']


def unauthenticated_user(view_func):
	@wraps(view_func)
	def wrapper_func(request, *args, **kwargs):
		if request.user.is_authenticated:
			return redirect('home')
		return view_func(request, *args, **kwargs)
	return wrapper_func


def _has_role(user, allowed_roles):
	return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name__in=allowed_roles).exists())


def allowed_users(allowed_roles=[]):
	"""Untuk halaman. Gunakan setelah @login_required. Peran tidak cocok -> 403."""
	def decorator(view_func):
		@wraps(view_func)
		def wrapper_func(request, *args, **kwargs):
			if _has_role(request.user, allowed_roles):
				return view_func(request, *args, **kwargs)
			return render(request, 'home/403.html', status=403)
		return wrapper_func
	return decorator


def api_allowed_users(allowed_roles=[]):
	"""Untuk API JSON: 401 bila belum masuk, 403 bila peran tidak cocok (bukan redirect)."""
	def decorator(view_func):
		@wraps(view_func)
		def wrapper_func(request, *args, **kwargs):
			if not request.user.is_authenticated:
				return JsonResponse({'error': 'unauthorized'}, status=401)
			if not _has_role(request.user, allowed_roles):
				return JsonResponse({'error': 'forbidden'}, status=403)
			return view_func(request, *args, **kwargs)
		return wrapper_func
	return decorator
