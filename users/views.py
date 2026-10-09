from django.contrib.auth import login, logout
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from config.utils import json_body

from . import auth_utils


@require_POST
def request_code(request):
	email = auth_utils.clean_email(json_body(request).get('email'))
	if not email:
		return JsonResponse({'error': 'email_invalid'}, status=400)
	try:
		auth_utils.issue_code(email)
	except auth_utils.RateLimited:
		return JsonResponse({'error': 'rate_limited'}, status=429)
	# Jawaban sama untuk email baru maupun lama: tidak membocorkan siapa yang terdaftar.
	return JsonResponse({'ok': True})


@require_POST
def verify(request):
	data = json_body(request)
	email = auth_utils.clean_email(data.get('email'))
	code = str(data.get('code', '')).strip()
	if not email or not (code.isdigit() and len(code) == 6):
		return JsonResponse({'error': 'code_invalid'}, status=400)
	result = auth_utils.verify_code(email, code)
	if not result:
		return JsonResponse({'error': 'code_wrong'}, status=400)
	user, created = result
	login(request, user)
	return JsonResponse({'ok': True, 'new_user': created})


@require_POST
def logout_view(request):
	logout(request)
	return JsonResponse({'ok': True})
