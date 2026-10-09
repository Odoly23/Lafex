from django.core.cache import cache
from django.db import models

CACHE_KEY = 'lafex.system_setting'


class SystemSetting(models.Model):
	"""Pengaturan sistem (satu baris). Diubah admin lewat halaman Pengaturan Sistem."""
	tutor_prompt_extra = models.TextField(
        blank=True, max_length=2000, verbose_name='Instrusaun adisionál ba Maun Lafaek',
        help_text='Ditambah ba prompt dasar (gaya, nada, topiku). Aturan dasar sistema la bele ubah.')
	payments_required = models.BooleanField(
        default=True, verbose_name='Presiza pakote (se la tika = gratis ba hotu)')
	free_turns_per_day = models.PositiveIntegerField(default=5, verbose_name='Dalan gratis kada loron (sein pakote)')
	paid_turns_per_day = models.PositiveIntegerField(default=150, verbose_name='Dalan kada loron (ho pakote)')

	class Meta:
		verbose_name = 'Konfigurasaun sistema'
		verbose_name_plural = 'Konfigurasaun sistema'

	def save(self, *args, **kwargs):
		self.pk = 1
		super().save(*args, **kwargs)
		cache.delete(CACHE_KEY)

	@classmethod
	def load(cls):
		"""Ambil pengaturan (di-cache sebentar agar tidak membebani database di setiap permintaan)."""
		obj = cache.get(CACHE_KEY)
		if obj is None:
			from django.conf import settings
			obj, _ = cls.objects.get_or_create(pk=1, defaults={
                'free_turns_per_day': settings.FREE_TURNS_PER_DAY,
                'paid_turns_per_day': settings.PAID_TURNS_PER_DAY,
            })
			cache.set(CACHE_KEY, obj, 30)
		return obj
