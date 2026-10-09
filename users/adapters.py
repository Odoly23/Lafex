"""Adapter allauth: hanya login sosial (Google/Facebook). Tidak ada pendaftaran/kata sandi lokal."""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.base import AuthError
from django.contrib.auth.models import Group
from django.shortcuts import redirect

MAX_NAME = 80


def ensure_student_role(user):
	if not user.groups.exists():
		user.groups.add(Group.objects.get_or_create(name='estudante')[0])


class AccountAdapter(DefaultAccountAdapter):
	def is_open_for_signup(self, request):
		return False  # pendaftaran lewat formulir/kata sandi ditutup; akun dibuat lewat login sosial atau kode email


class SocialAccountAdapter(DefaultSocialAccountAdapter):
	def is_open_for_signup(self, request, sociallogin):
		return True  # daftar otomatis pada login sosial pertama

	def pre_social_login(self, request, sociallogin):
		# Tanpa email kita tidak bisa mencocokkan/membuat akun: kembali ke halaman masuk dengan pesan.
		if not sociallogin.is_existing and not (sociallogin.user.email or '').strip():
			raise ImmediateHttpResponse(redirect('/login/?error=social_no_email'))

	def populate_user(self, request, sociallogin, data):
		user = super().populate_user(request, sociallogin, data)
		full = ' '.join(filter(None, [data.get('first_name'), data.get('last_name')])) or data.get('name') or ''
		user.name = ' '.join(str(full).split())[:MAX_NAME]
		return user

	def save_user(self, request, sociallogin, form=None):
		user = super().save_user(request, sociallogin, form)
		user.set_unusable_password()
		user.save(update_fields=['password'])
		ensure_student_role(user)
		return user

	def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
		reason = 'social_cancelled' if error == AuthError.CANCELLED else 'social_error'
		raise ImmediateHttpResponse(redirect(f'/login/?error={reason}'))
