from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .adapters import ensure_student_role


@receiver(user_logged_in)
def heal_missing_role(sender, request, user, **kwargs):
	"""Siapa pun yang berhasil masuk (kode email atau sosial) pasti punya peran; tanpa itu semua halaman memberi 403."""
	ensure_student_role(user)
