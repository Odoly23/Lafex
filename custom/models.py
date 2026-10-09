from django.db import models


class Municipality(models.Model):
	code = models.CharField(max_length=5, null=True)
	name = models.CharField(max_length=50, verbose_name="Naran")
	hckey = models.CharField(max_length=10, null=True)  # kunci wilayah di Highcharts Maps (hc-key), mis. 'tl-dl'

	class Meta:
		ordering = ['name']
		verbose_name = 'Munisipiu'
		verbose_name_plural = 'Munisipiu'

	def __str__(self):
		template = '{0.name}'
		return template.format(self)
