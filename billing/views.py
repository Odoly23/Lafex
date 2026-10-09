from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import api_login_required
from accounts.views import body
from curriculum.models import band_for_level

from . import services
from .models import Plan


def me_payload(user):
    exp = services.expires_at(user)
    return {
        'email': user.email, 'level': user.level, 'band': band_for_level(user.level),
        'placement_done': user.placement_done,
        'active': services.is_active(user), 'expires_at': exp.isoformat() if exp else None,
        'turns_left': services.turns_left(user),
    }


@require_GET
@api_login_required
def me(request):
    plans = [{'code': p.code, 'label': p.label, 'price_usd': str(p.price_usd)} for p in Plan.objects.filter(active=True)]
    return JsonResponse({**me_payload(request.user), 'plans': plans})


@require_POST
@api_login_required
def redeem(request):
    try:
        services.redeem(request.user, body(request).get('code'))
    except services.VoucherError as e:
        return JsonResponse({'error': e.code}, status=400)
    return JsonResponse(me_payload(request.user))
