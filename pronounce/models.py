from django.conf import settings
from django.db import models
from django.utils import timezone

from curriculum.models import BANDS


class PronPhrase(models.Model):
	text_en = models.CharField(max_length=200, verbose_name='Sentensa (Inglés)')
	text_tet = models.CharField(max_length=200, blank=True, verbose_name='Tradusaun (Tetun)')
	band = models.CharField(max_length=12, choices=BANDS, default='beginner', verbose_name='Band nível')
	active = models.BooleanField(default=True, verbose_name='Ativu')

	class Meta:
		ordering = ['band', 'id']
		verbose_name = 'Sentensa pronunciation'
		verbose_name_plural = 'Sentensa pronunciation'

	def __str__(self):
		return self.text_en[:60]


class PronAttempt(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pron_attempts',
                             verbose_name='Estudante')
	phrase = models.ForeignKey(PronPhrase, on_delete=models.CASCADE, verbose_name='Sentensa')
	transcript = models.CharField(max_length=300, blank=True, verbose_name='Neʼebé rona')
	confidence = models.FloatField(null=True, blank=True, verbose_name='Konfiansa rekonhesedór')
	score = models.PositiveSmallIntegerField(verbose_name='Pontu')
	detail = models.JSONField(default=list, blank=True, verbose_name='Detalle liafuan')
	created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Data')

	class Meta:
		ordering = ['-created_at']
		verbose_name = 'Tentativa pronunciation'
		verbose_name_plural = 'Tentativa pronunciation'
