from django.conf import settings
from django.db import models
from django.utils import timezone


class Session(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions',
                             verbose_name='Estudante')
	mission = models.ForeignKey('curriculum.Mission', on_delete=models.PROTECT, verbose_name='Misaun')
	level_start = models.CharField(max_length=2, verbose_name='Nível hahú')
	started_at = models.DateTimeField(default=timezone.now, verbose_name='Hahú')
	finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Remata')
	score = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Pontu')
	level_end = models.CharField(max_length=2, blank=True, verbose_name='Nível remata')
	summary = models.JSONField(default=dict, blank=True, verbose_name='Rezumu')  # headline, tips, vocab, corrections

	class Meta:
		ordering = ['-started_at']
		indexes = [models.Index(fields=['user', 'finished_at'])]
		verbose_name = 'Sesaun'
		verbose_name_plural = 'Sesaun'


class Turn(models.Model):
	session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='turns', verbose_name='Sesaun')
	idx = models.PositiveSmallIntegerField(verbose_name='Orden')
	role = models.CharField(max_length=9, choices=[('user', 'Estudante'), ('assistant', 'Lafaek')], verbose_name='Papél')
	text = models.TextField(verbose_name='Teksu')
	correction = models.TextField(blank=True, verbose_name='Koreksaun')
	explanation = models.TextField(blank=True, verbose_name='Esplikasaun')
	created_at = models.DateTimeField(default=timezone.now, verbose_name='Data kria')

	class Meta:
		ordering = ['idx']
		unique_together = [('session', 'idx')]
		verbose_name = 'Dalan koalia'
		verbose_name_plural = 'Dalan koalia'
