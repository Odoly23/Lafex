"""Vokabulario awal (Tetun -> Inglés). Idempoten. Teks Tetun WAJIB ditinjau penutur asli."""

CATEGORIES = [
    {'slug': 'eskola', 'name_tet': 'Eskola', 'name_en': 'School', 'emoji': '🏫', 'order': 1, 'items': [
        ('eskola', 'school', 'I go to school every day.'), ('mestre', 'teacher', 'My teacher is kind.'),
        ('estudante', 'student', 'She is a good student.'), ('livru', 'book', 'This book is interesting.'),
        ('kaderno', 'notebook', 'I write in my notebook.'), ('kaneta', 'pen', 'Can I borrow your pen?'),
        ('lapis', 'pencil', 'I need a pencil.'), ('kadeira', 'chair', 'Please sit on the chair.'),
        ('meza', 'table', 'The books are on the table.'), ('klase', 'class', 'The class starts at eight.'),
    ]},
    {'slug': 'merkadu', 'name_tet': 'Merkadu', 'name_en': 'Market', 'emoji': '🛒', 'order': 2, 'items': [
        ('merkadu', 'market', 'I go to the market on Saturday.'), ('folin', 'price', 'What is the price?'),
        ('osan', 'money', 'I do not have enough money.'), ('sosa', 'buy', 'I want to buy some fish.'),
        ('faan', 'sell', 'They sell fresh vegetables.'), ('ikan', 'fish', 'The fish is fresh.'),
        ('fos', 'rice', 'I would like a kilo of rice.'), ('modo', 'vegetables', 'We eat vegetables every day.'),
        ('fuan', 'fruit', 'This fruit is sweet.'), ('masin', 'salt', 'Please pass the salt.'),
    ]},
    {'slug': 'kantor', 'name_tet': 'Kantór', 'name_en': 'Office', 'emoji': '🏢', 'order': 3, 'items': [
        ('kantór', 'office', 'My office is in Dili.'), ('serbisu', 'work', 'I work from Monday to Friday.'),
        ('xefe', 'boss', 'My boss is in a meeting.'), ('kolega', 'colleague', 'My colleague helps me.'),
        ('reuniaun', 'meeting', 'The meeting is at ten.'), ('komputadór', 'computer', 'I use a computer every day.'),
        ('telemóvel', 'mobile phone', 'Please turn off your mobile phone.'), ('dokumentu', 'document', 'I need to print this document.'),
        ('salariu', 'salary', 'The salary is paid monthly.'), ('horáriu', 'schedule', 'What is your schedule today?'),
    ]},
]


def run():
	from .models import VocabCategory, VocabItem
	n = 0
	for c in CATEGORIES:
		cat, _ = VocabCategory.objects.update_or_create(slug=c['slug'], defaults={
            k: c[k] for k in ('name_tet', 'name_en', 'emoji', 'order')})
		for i, (tet, en, ex) in enumerate(c['items'], 1):
			VocabItem.objects.update_or_create(category=cat, en=en, defaults={'tet': tet, 'example_en': ex, 'order': i})
			n += 1
	return len(CATEGORIES), n
