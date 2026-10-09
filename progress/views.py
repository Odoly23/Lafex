from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response

from config.api import APIAll, body
from config.decorators import ALL_ROLES, allowed_users
from config.user_utils import user_group

from . import services
from .models import Certificate

MAX_NAME = 80


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def ProfilePage(request):
	# Tanpa data pribadi di HTML (nama/email diisi JavaScript lewat API): halaman bisa dicache.
	context = {'group': user_group(request.user), 'page': 'profil', 'title': 'Perfíl'}
	return render(request, 'progress/profile.html', context)


def CertificatePage(request, code):
	"""Halaman sertifikat yang bisa dicetak. Publik (tanpa login) agar pihak lain bisa memverifikasi lewat kode.
    Hanya memuat nama, level, tanggal, dan kode; tidak ada email."""
	cert = get_object_or_404(Certificate, code=code.upper())
	name = cert.user.name or cert.name  # nama terkini (siswa bisa mengisinya setelah sertifikat terbit)
	return render(request, 'progress/certificate.html', {'cert': cert, 'display_name': name, 'title': f'Sertifikadu {cert.level}'})


class APIProfile(APIAll):
	def get(self, request, format=None):
		u = request.user
		certs = [{'code': c.code, 'level': c.level, 'issued_at': c.issued_at.isoformat()} for c in u.certificates.all()]
		return Response({
            'email': u.email, 'name': u.name, 'level': u.level, 'points': u.points,
            'streak': services.current_streak(u), 'best_streak': u.best_streak, 'certificates': certs,
        })

	def post(self, request, format=None):
		name = ' '.join(str(body(request).get('name', '')).split())[:MAX_NAME]
		request.user.name = name
		request.user.save(update_fields=['name'])
		return Response({'name': name})
