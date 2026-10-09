from django.db import models

BANDS = [('beginner', 'Hahú (A1-A2)'), ('intermediate', 'Média (B1-B2)'), ('advanced', 'Avansadu (C1-C2)')]
BAND_LEVELS = {'beginner': ('A1', 'A2'), 'intermediate': ('B1', 'B2'), 'advanced': ('C1', 'C2')}


def band_for_level(level):
	for band, levels in BAND_LEVELS.items():
		if level in levels:
			return band
	return 'beginner'


class Scenario(models.Model):
	slug = models.SlugField(unique=True, verbose_name='Kódigu')
	title_tet = models.CharField(max_length=80, verbose_name='Títulu (Tetun)')
	title_en = models.CharField(max_length=80, verbose_name='Títulu (Inglés)')
	emoji = models.CharField(max_length=8, blank=True, verbose_name='Emoji')
	order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
	active = models.BooleanField(default=True, verbose_name='Ativu')

	class Meta:
		ordering = ['order']
		verbose_name = 'Situasaun'
		verbose_name_plural = 'Situasaun'

	def __str__(self):
		return self.title_en


class Mission(models.Model):
	"""Satu role-play: AI memerankan `ai_role`, siswa harus mencapai `goal_en`."""
	scenario = models.ForeignKey(Scenario, null=True, blank=True, on_delete=models.CASCADE,
                                 related_name='missions', verbose_name='Situasaun')
	slug = models.SlugField(unique=True, verbose_name='Kódigu')
	band = models.CharField(max_length=12, choices=BANDS, verbose_name='Band nível')
	order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
	title_tet = models.CharField(max_length=100, verbose_name='Títulu (Tetun)')
	title_en = models.CharField(max_length=100, verbose_name='Títulu (Inglés)')
	goal_tet = models.TextField(verbose_name='Objetivu (Tetun, ba estudante)')
	goal_en = models.TextField(verbose_name='Objetivu (Inglés, ba AI)')
	ai_role = models.TextField(verbose_name='Papél no situasaun AI (Inglés)')
	rubric = models.JSONField(default=list, verbose_name='Rubrika avaliasaun (Inglés)')
	max_turns = models.PositiveSmallIntegerField(default=12, verbose_name='Dalan maksimu')
	is_placement = models.BooleanField(default=False, verbose_name='Teste nível')
	active = models.BooleanField(default=True, verbose_name='Ativu')

	class Meta:
		ordering = ['scenario__order', 'band', 'order']
		verbose_name = 'Misaun'
		verbose_name_plural = 'Misaun'

	def __str__(self):
		return f'{self.slug} [{self.band}]'
