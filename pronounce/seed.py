"""Kalimat latihan pronunciation awal. Idempoten (kunci: teks Inglés)."""

PHRASES = [
    ('beginner', 'Good morning, my name is Maria.'), ('beginner', 'How much is this?'),
    ('beginner', 'I live in Dili.'), ('beginner', 'Thank you very much.'),
    ('beginner', 'Where is the bus station?'), ('beginner', 'I like fish and rice.'),
    ('intermediate', 'Could you tell me how to get to the hospital?'),
    ('intermediate', 'I would like to book a room for two nights.'),
    ('intermediate', 'I have been studying English for six months.'),
    ('intermediate', 'What time does the meeting start tomorrow?'),
    ('intermediate', 'My brother works in a small office near the market.'),
    ('advanced', 'Unfortunately, my luggage did not arrive on time.'),
    ('advanced', 'I would appreciate it if you could reduce the price a little.'),
    ('advanced', 'The weather has been extremely unpredictable lately.'),
    ('advanced', 'Despite the delay, we managed to finish the project.'),
]


def run():
	from .models import PronPhrase
	for band, text in PHRASES:
		PronPhrase.objects.update_or_create(text_en=text, defaults={'band': band})
	return len(PHRASES)
