def user_group(user):
	"""Nama peran (group) pertama pengguna, atau None."""
	group = user.groups.first()
	return group.name if group else None
