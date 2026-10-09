from functools import wraps

from django.http import JsonResponse


def api_login_required(view):
    """Seperti login_required, tapi menjawab JSON 401 (bukan redirect) untuk klien API."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'unauthorized'}, status=401)
        return view(request, *args, **kwargs)
    return wrapper
