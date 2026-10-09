from django.conf import settings
from django.db import models
from django.utils import timezone

from curriculum.models import BANDS

ANSWERS = [('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')]


class QuizQuestion(models.Model):
	question = models.CharField(max_length=300, verbose_name='Pergunta (Inglés)')
	choice_a = models.CharField(max_length=120, verbose_name='Opsaun A')
	choice_b = models.CharField(max_length=120, verbose_name='Opsaun B')
	choice_c = models.CharField(max_length=120, verbose_name='Opsaun C')
	choice_d = models.CharField(max_length=120, verbose_name='Opsaun D')
	answer = models.CharField(max_length=1, choices=ANSWERS, verbose_name='Resposta loos')
	explanation_tet = models.CharField(max_length=300, blank=True, verbose_name='Esplikasaun (Tetun)')
	band = models.CharField(max_length=12, choices=BANDS, default='beginner', verbose_name='Band nível')
	active = models.BooleanField(default=True, verbose_name='Ativu')

	class Meta:
		ordering = ['band', 'id']
		verbose_name = 'Pergunta quiz'
		verbose_name_plural = 'Pergunta quiz'

	def __str__(self):
		return self.question[:60]

	def choices(self):
		return {'a': self.choice_a, 'b': self.choice_b, 'c': self.choice_c, 'd': self.choice_d}


class QuizAttempt(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts',
                             verbose_name='Estudante')
	started_at = models.DateTimeField(default=timezone.now, verbose_name='Hahú')
	deadline = models.DateTimeField(verbose_name='Limite oras')
	finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Remata')
	question_ids = models.JSONField(default=list, verbose_name='Pergunta')
	answers = models.JSONField(default=dict, blank=True, verbose_name='Resposta')
	score = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Loos')
	total = models.PositiveSmallIntegerField(default=0, verbose_name='Total')
	late = models.BooleanField(default=False, verbose_name='Liu oras')

	class Meta:
		ordering = ['-started_at']
		verbose_name = 'Tentativa quiz'
		verbose_name_plural = 'Tentativa quiz'
