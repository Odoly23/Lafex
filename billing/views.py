from rest_framework.response import Response

from config.api import APIAll, body
from config.user_utils import user_group
from curriculum.models import band_for_level

from . import services
from .models import Plan, Voucher


def me_payload(user):
	exp = services.expires_at(user)
	return {
        'email': user.email, 'group': user_group(user), 'level': user.level, 'band': band_for_level(user.level),
        'placement_done': user.placement_done,
        'active': services.is_active(user), 'expires_at': exp.isoformat() if exp else None,
        'turns_left': services.turns_left(user),
    }


class APIMe(APIAll):
	def get(self, request, format=None):
		plans = [{'code': p.code, 'label': p.label, 'price_usd': str(p.price_usd)}
                 for p in Plan.objects.filter(active=True)]
		return Response({**me_payload(request.user), 'plans': plans})


class APIRedeem(APIAll):
	def post(self, request, format=None):
		try:
			services.redeem(request.user, body(request).get('code'))
		except services.VoucherError as e:
			return Response({'error': e.code}, status=400)
		return Response(me_payload(request.user))
