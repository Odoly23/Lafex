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


class VoucherBatch(models.Model):
	"""Satu kelompok voucher yang dicetak untuk satu toko/penjual. Bisa dibatalkan sekaligus."""
	label = models.CharField(max_length=80, verbose_name='Toko / penjual (label)')
	plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name='Pakote')
	quantity = models.PositiveIntegerField(verbose_name='Kuantidade')
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+', verbose_name='Kria husi')
	created_at = models.DateTimeField(default=timezone.now, verbose_name='Data kria')
	valid_until = models.DateTimeField(verbose_name='Válidu to\'o')
	voided_at = models.DateTimeField(null=True, blank=True, verbose_name='Kansela iha')

	class Meta:
		ordering = ['-created_at']
		verbose_name = 'Batch vaucher'
		verbose_name_plural = 'Batch vaucher'

	def __str__(self):
		return f'#{self.pk} {self.label}'

	@property
	def active(self):
		return self.voided_at is None and self.valid_until > timezone.now()


class VoucherQuerySet(models.QuerySet):
	def available(self):
		"""Belum dipakai, tidak dibatalkan, dan belum kedaluwarsa."""
		now = timezone.now()
		return self.filter(used_by__isnull=True, voided_at__isnull=True).filter(
            models.Q(batch__isnull=True) | models.Q(batch__voided_at__isnull=True, batch__valid_until__gt=now))


class Voucher(models.Model):
	"""Kartu voucher. Kode rahasia TIDAK disimpan (hanya hash); `serial` adalah nomor cetak yang aman ditampilkan."""
	serial = models.CharField(max_length=24, unique=True, verbose_name='Nu. seri')
	code_hash = models.CharField(max_length=64, unique=True)
	batch = models.ForeignKey(VoucherBatch, null=True, blank=True, on_delete=models.PROTECT, related_name='vouchers',
                              verbose_name='Batch')
	plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name='Pakote')
	created_at = models.DateTimeField(default=timezone.now, verbose_name='Data kria')
	used_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Uza husi')
	used_at = models.DateTimeField(null=True, blank=True, verbose_name='Data uza')
	voided_at = models.DateTimeField(null=True, blank=True, verbose_name='Kansela iha')

	objects = VoucherQuerySet.as_manager()

	class Meta:
		verbose_name = 'Vaucher'
		verbose_name_plural = 'Vaucher'

	def __str__(self):
		return self.serial

	@property
	def status(self):
		"""used | void | expired | available"""
		if self.used_by_id or self.used_at:
			return 'used'
		if self.voided_at or (self.batch_id and self.batch.voided_at):
			return 'void'
		if self.batch_id and self.batch.valid_until <= timezone.now():
			return 'expired'
		return 'available'


class RedeemAttempt(models.Model):
	"""Catatan percobaan memasukkan kode (untuk membatasi tebak-tebakan)."""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
	ip = models.CharField(max_length=45, blank=True)
	ok = models.BooleanField(default=False)
	created_at = models.DateTimeField(default=timezone.now, db_index=True)


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
