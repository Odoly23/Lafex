from django.conf import settings
from django.db import models
from django.utils import timezone


class Plan(models.Model):
	code = models.SlugField(unique=True)            # 1d, 3d, 7d, 30d, 365d
	label = models.CharField(max_length=40)          # tampilan: "7 loron"
	hours = models.PositiveIntegerField()
	price_usd = models.DecimalField(max_digits=6, decimal_places=2)
	sort = models.PositiveSmallIntegerField(default=0)
	active = models.BooleanField(default=True)

	class Meta:
		ordering = ['sort']

	def __str__(self):
		return f'{self.label} (${self.price_usd})'


class Voucher(models.Model):
	code = models.CharField(max_length=20, unique=True)
	plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
	created_at = models.DateTimeField(default=timezone.now)
	used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
	used_at = models.DateTimeField(null=True, blank=True)

	def __str__(self):
		return self.code


class Entitlement(models.Model):
	"""Satu baris per pengguna: kapan paket berakhir. Voucher baru menambah waktu."""
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='entitlement')
	expires_at = models.DateTimeField()

	@property
	def active(self):
		return self.expires_at > timezone.now()


class UsageDay(models.Model):
	"""Jatah giliran per hari (batas pemakaian wajar)."""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	day = models.DateField()
	turns = models.PositiveIntegerField(default=0)

	class Meta:
		unique_together = [('user', 'day')]
