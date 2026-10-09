from django.core.management.base import BaseCommand

from curriculum import seed


class Command(BaseCommand):
    help = 'Isi/perbarui skenario dan misi awal (idempoten).'

    def handle(self, **opts):
        s, m = seed.run()
        self.stdout.write(f'{s} skenario, {m} misi siap.')
