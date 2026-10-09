from django.core.management.base import BaseCommand

from curriculum import seed as curriculum_seed
from custom import seed as custom_seed
from pronounce import seed as pron_seed
from quiz import seed as quiz_seed
from vocab import seed as vocab_seed


class Command(BaseCommand):
	help = 'Isi/perbarui semua data awal (misi, vokabulario, soal quiz, kalimat pronunciation). Aman diulang.'

	def handle(self, **opts):
		s, m = curriculum_seed.run()
		c, v = vocab_seed.run()
		custom_seed.run()
		self.stdout.write(f'{s} skenario, {m} misi | {c} kategoria, {v} vokabulario | '
                          f'{quiz_seed.run()} soal quiz | {pron_seed.run()} kalimat pronunciation | {len(custom_seed.MUNICIPALITIES)} munisipiu')
