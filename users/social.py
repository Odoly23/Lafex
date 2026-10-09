from django.conf import settings

LABELS = {'google': 'Google', 'facebook': 'Facebook'}


def enabled_providers():
	"""Penyedia login sosial yang sudah dikonfigurasi (ada client id/secret). Tombol hanya muncul untuk ini."""
	conf = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {})
	return [{'id': pid, 'name': LABELS.get(pid, pid.title())} for pid, c in conf.items() if c.get('APPS')]
