import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from users.models import LEVELS, User

from .models import Activity, Certificate

# Aturan poin (satu tempat agar mudah diubah)
POINTS = {
    'situasaun_finish': 10,   # + nilai // 10
    'chat_finish': 5,         # + nilai // 20
    'vocab_known': 1,         # per kata yang baru dikuasai
    'grammar': 2,             # + 3 bila tanpa kesalahan
    'grammar_perfect': 3,
    'quiz_correct': 2,        # per jawaban benar
    'quiz_perfect': 5,
    'pron_divisor': 10,       # nilai // 10 per frasa
}


@transaction.atomic
def award(user, kind, points=0, ref=''):
	"""Catat kegiatan, tambah poin, dan perbarui streak (hari berturut-turut, zona waktu Dili)."""
	today = timezone.localdate()
	u = User.objects.select_for_update().get(pk=user.pk)
	if u.last_active != today:
		u.streak = u.streak + 1 if u.last_active == today - timedelta(days=1) else 1
		u.best_streak = max(u.best_streak, u.streak)
		u.last_active = today
	u.points += max(0, int(points))
	u.save(update_fields=['points', 'streak', 'best_streak', 'last_active'])
	Activity.objects.create(user=u, kind=kind, points=max(0, int(points)), ref=str(ref)[:60])
	for f in ('points', 'streak', 'best_streak', 'last_active'):  # instance pemanggil ikut segar
		setattr(user, f, getattr(u, f))
	return u


def current_streak(user):
	"""Streak yang ditampilkan: putus bila kemarin pun tidak belajar."""
	today = timezone.localdate()
	return user.streak if user.last_active in (today, today - timedelta(days=1)) else 0


def issue_certificate(user, level):
	"""Sertifikat untuk level A2 ke atas; satu per level per siswa."""
	if level not in LEVELS or LEVELS.index(level) < 1:
		return None
	cert, _ = Certificate.objects.get_or_create(
        user=user, level=level,
        defaults={'code': 'LFX-' + secrets.token_hex(4).upper(), 'name': user.name})
	return cert
