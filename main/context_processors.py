from config.user_utils import user_group

from .strings import TETUN


def strings(request):
	user = getattr(request, 'user', None)
	group = user_group(user) if user is not None and user.is_authenticated else None
	# 'group' dari context view (jika ada) menimpa nilai ini.
	return {'T': TETUN, 'group': group}
