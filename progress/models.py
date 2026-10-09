from django.conf import settings
from django.db import models
from django.utils import timezone

KINDS = [
    ('chat', 'Ngobrol bebas'), ('situasaun', 'Situasaun'), ('vocab', 'Vokabulario'),
    ('grammar', 'Grammar fix'), ('quiz', 'Quiz'), ('pron', 'Pronunciation'),
]


class Activity(models.Model):
	"""Satu catatan setiap kegiatan belajar. Dipakai untuk poin, streak, dan 'siswa aktif hari ini'."""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities',
                             verbose_name='Estudante')
	kind = models.CharField(max_length=10, choices=KINDS, verbose_name='Tipu')
	points = models.PositiveSmallIntegerField(default=0, verbose_name='Pontu')
	ref = models.CharField(max_length=60, blank=True, verbose_name='Referénsia')
	created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Data')

	class Meta:
		ordering = ['-created_at']
		verbose_name = 'Atividade'
		verbose_name_plural = 'Atividade'


class Certificate(models.Model):
	"""Sertifikat per level CEFR yang dicapai lewat belajar (bukan lewat tes penempatan)."""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates',
                             verbose_name='Estudante')
	level = models.CharField(max_length=2, verbose_name='Nível')
	code = models.CharField(max_length=16, unique=True, verbose_name='Kódigu verifikasaun')
	name = models.CharField(max_length=80, blank=True, verbose_name='Naran iha sertifikadu')
	issued_at = models.DateTimeField(default=timezone.now, verbose_name='Data emite')

	class Meta:
		unique_together = [('user', 'level')]
		ordering = ['-issued_at']
		verbose_name = 'Sertifikadu'
		verbose_name_plural = 'Sertifikadu'
