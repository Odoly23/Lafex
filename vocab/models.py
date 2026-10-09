from django.conf import settings
from django.db import models
from django.utils import timezone


class VocabCategory(models.Model):
	slug = models.SlugField(unique=True, verbose_name='Kódigu')
	name_tet = models.CharField(max_length=60, verbose_name='Naran (Tetun)')
	name_en = models.CharField(max_length=60, verbose_name='Naran (Inglés)')
	emoji = models.CharField(max_length=8, blank=True, verbose_name='Emoji')
	order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
	active = models.BooleanField(default=True, verbose_name='Ativu')

	class Meta:
		ordering = ['order', 'name_tet']
		verbose_name = 'Kategoria kosa kata'
		verbose_name_plural = 'Kategoria kosa kata'

	def __str__(self):
		return self.name_en


class VocabItem(models.Model):
	category = models.ForeignKey(VocabCategory, on_delete=models.CASCADE, related_name='items', verbose_name='Kategoria')
	tet = models.CharField(max_length=80, verbose_name='Tetun')
	en = models.CharField(max_length=80, verbose_name='Inglés')
	example_en = models.CharField(max_length=200, blank=True, verbose_name='Ezemplu sentensa (Inglés)')
	order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
	active = models.BooleanField(default=True, verbose_name='Ativu')

	class Meta:
		ordering = ['order', 'id']
		verbose_name = 'Kosa kata'
		verbose_name_plural = 'Kosa kata'

	def __str__(self):
		return f'{self.tet} = {self.en}'


class UserVocab(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Estudante')
	item = models.ForeignKey(VocabItem, on_delete=models.CASCADE, verbose_name='Kosa kata')
	known = models.BooleanField(default=False, verbose_name='Hatene ona')
	rewarded = models.BooleanField(default=False, verbose_name='Pontu fó ona')  # poin hanya sekali per kata
	updated_at = models.DateTimeField(default=timezone.now, verbose_name='Atualiza')

	class Meta:
		unique_together = [('user', 'item')]
		verbose_name = 'Progresu kosa kata'
		verbose_name_plural = 'Progresu kosa kata'
