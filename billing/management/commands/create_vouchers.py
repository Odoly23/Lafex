from django.core.management.base import BaseCommand, CommandError

from billing import services
from billing.models import Plan


class Command(BaseCommand):
	help = 'Buat voucher sekali pakai. Contoh: manage.py create_vouchers 7d 10'

	def add_arguments(self, parser):
		parser.add_argument('plan')
		parser.add_argument('count', type=int, nargs='?', default=1)

	def handle(self, plan, count, **opts):
		if not Plan.objects.filter(code=plan).exists():
			raise CommandError('Paket tidak dikenal. Pilihan: ' + ', '.join(Plan.objects.values_list('code', flat=True)))
		for code in services.create_vouchers(plan, min(max(count, 1), 500)):
			self.stdout.write(code)
