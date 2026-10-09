from django.core.management.base import BaseCommand, CommandError

from billing import services
from billing.models import Plan


class Command(BaseCommand):
	help = 'Buat batch voucher sekali pakai (nomor seri + kode rahasia). Contoh: manage.py create_vouchers 7d 10 "Toko Maria"'

	def add_arguments(self, parser):
		parser.add_argument('plan')
		parser.add_argument('count', type=int, nargs='?', default=1)
		parser.add_argument('label', nargs='?', default='CLI')

	def handle(self, plan, count, label, **opts):
		obj = Plan.objects.filter(code=plan).first()
		if not obj:
			raise CommandError('Paket tidak dikenal. Pilihan: ' + ', '.join(Plan.objects.values_list('code', flat=True)))
		batch, rows = services.create_batch(obj, min(max(count, 1), 500), label)
		self.stderr.write(f'Batch #{batch.pk}: kode hanya ditampilkan sekarang (database hanya menyimpan hash).')
		for serial, code in rows:
			self.stdout.write(f'{serial}\t{code}')
