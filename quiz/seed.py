"""Soal quiz awal. Idempoten (kunci: teks pertanyaan). Penjelasan Tetun WAJIB ditinjau penutur asli."""

Q = [
    # beginner
    ('beginner', 'I ___ a student.', 'is', 'am', 'are', 'be', 'b', "Ho 'I' uza 'am'."),
    ('beginner', 'She ___ to school every day.', 'go', 'goes', 'going', 'gone', 'b', "Ho 'she/he/it' aumenta -s: goes."),
    ('beginner', 'What is your ___?', 'name', 'names', 'naming', 'named', 'a', "'What is your name?' = Ita-nia naran saida?"),
    ('beginner', 'How ___ are you?', 'year', 'years', 'old', 'age', 'c', "'How old are you?' = Ita nia tinan hira?"),
    ('beginner', 'This is ___ apple.', 'a', 'an', 'the', 'two', 'b', "Molok lia-fuan ne'ebé hahú ho vogal (a, e, i, o, u) uza 'an'."),
    ('beginner', 'They ___ at home now.', 'is', 'am', 'are', 'be', 'c', "Ho 'they/we/you' uza 'are'."),
    ('beginner', 'Where ___ you from?', 'is', 'are', 'am', 'do', 'b', "'Where are you from?' = Ita mai husi ne'ebé?"),
    ('beginner', 'I have two ___.', 'book', 'books', 'bookes', 'a book', 'b', "Liu ida: aumenta -s (books)."),
    # intermediate
    ('intermediate', 'I ___ to the market yesterday.', 'go', 'goes', 'went', 'going', 'c', "Pasadu husi 'go' mak 'went'."),
    ('intermediate', 'If it rains, we ___ at home.', 'stay', 'stayed', 'will stay', 'staying', 'c', "Ho 'if' + prezente, uza 'will' iha parte daruak."),
    ('intermediate', 'She has lived here ___ 2020.', 'for', 'since', 'from', 'at', 'b', "'since' uza ho data; 'for' uza ho durasaun."),
    ('intermediate', 'He is ___ than his brother.', 'tall', 'taller', 'tallest', 'more tall', 'b', "Komparativu: tall -> taller."),
    # advanced
    ('advanced', 'I wish I ___ more time to study.', 'have', 'had', 'will have', 'having', 'b', "'I wish' + pasadu (had) hatudu hakarak ne'ebé la loos ona."),
    ('advanced', 'The report ___ by the manager yesterday.', 'wrote', 'was written', 'is writing', 'has wrote', 'b', "Pasivu: was/were + particípiu (written)."),
    ('advanced', 'Hardly ___ the door when the phone rang.', 'I opened', 'had I opened', 'did I opened', 'I have opened', 'b', "'Hardly' iha ulun: 'had' + sujeitu (inversaun)."),
]


def run():
	from .models import QuizQuestion
	for band, q, a, b, c, d, ans, expl in Q:
		QuizQuestion.objects.update_or_create(question=q, defaults={
            'band': band, 'choice_a': a, 'choice_b': b, 'choice_c': c, 'choice_d': d, 'answer': ans, 'explanation_tet': expl})
	return len(Q)
