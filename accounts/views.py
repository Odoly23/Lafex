import json

from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from . import services


def body(request):
    try:
        data = json.loads(request.body or b'{}')
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


@require_POST
def request_code(request):
    email = services.clean_email(body(request).get('email'))
    if not email:
        return JsonResponse({'error': 'email_invalid'}, status=400)
    try:
        services.issue_code(email)
    except services.RateLimited:
        return JsonResponse({'error': 'rate_limited'}, status=429)
    # Jawaban sama untuk email baru maupun lama: tidak membocorkan siapa yang terdaftar.
    return JsonResponse({'ok': True})


@require_POST
def verify(request):
    data = body(request)
    email = services.clean_email(data.get('email'))
    code = str(data.get('code', '')).strip()
    if not email or not (code.isdigit() and len(code) == 6):
        return JsonResponse({'error': 'code_invalid'}, status=400)
    result = services.verify_code(email, code)
    if not result:
        return JsonResponse({'error': 'code_wrong'}, status=400)
    user, created = result
    login(request, user)
    return JsonResponse({'ok': True, 'new_user': created})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'ok': True})
