from django.conf import settings
from django.db import models
from django.utils import timezone


class MonitorLog(models.Model):
	"""Catatan audit: guru/admin mana yang membuka chat siswa mana. Siswa diberi tahu di Perfíl bahwa chat bisa dilihat guru."""
	viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='monitor_views',
                               verbose_name='Hare husi')
	session = models.ForeignKey('tutor.Session', on_delete=models.CASCADE, related_name='monitor_logs', verbose_name='Sesaun')
	viewed_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Data')

	class Meta:
		ordering = ['-viewed_at']
		verbose_name = 'Log monitorizasaun'
		verbose_name_plural = 'Log monitorizasaun'
