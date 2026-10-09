from django.conf import settings
from django.db import models
from django.utils import timezone


class Plan(models.Model):
	code = models.SlugField(unique=True, verbose_name='Kódigu')  # 1d, 3d, 7d, 30d, 365d
	label = models.CharField(max_length=40, verbose_name='Naran pakote')  # mis. "Loron 7"
	hours = models.PositiveIntegerField(verbose_name='Oras')
	price_usd = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Folin (USD)')
	sort = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
	active = models.BooleanField(default=True, verbose_name='Ativu')

	class Meta:
		ordering = ['sort']
		verbose_name = 'Pakote'
		verbose_name_plural = 'Pakote'

	def __str__(self):
		return f'{self.label} (${self.price_usd})'


class Voucher(models.Model):
	code = models.CharField(max_length=20, unique=True, verbose_name='Kódigu')
	plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name='Pakote')
	created_at = models.DateTimeField(default=timezone.now, verbose_name='Data kria')
	used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Uza husi')
	used_at = models.DateTimeField(null=True, blank=True, verbose_name='Data uza')

	class Meta:
		verbose_name = 'Vaucher'
		verbose_name_plural = 'Vaucher'

	def __str__(self):
		return self.code


class Entitlement(models.Model):
	"""Satu baris per pengguna: kapan paket berakhir. Voucher baru menambah waktu."""
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='entitlement', verbose_name='Estudante')
	expires_at = models.DateTimeField(verbose_name='Remata iha')

	class Meta:
		verbose_name = 'Asesu pakote'
		verbose_name_plural = 'Asesu pakote'

	@property
	def active(self):
		return self.expires_at > timezone.now()


class UsageDay(models.Model):
	"""Jatah giliran per hari (batas pemakaian wajar)."""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Estudante')
	day = models.DateField(verbose_name='Loron')
	turns = models.PositiveIntegerField(default=0, verbose_name='Dalan')

	class Meta:
		unique_together = [('user', 'day')]
		verbose_name = 'Uzu loron-loron'
		verbose_name_plural = 'Uzu loron-loron'
