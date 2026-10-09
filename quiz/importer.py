"""Import soal massal: 'pertanyaan | A | B | C | D | jawaban(a-d) | penjelasan Tetun (opsional)'."""
MAX_LINES = 100


def parse_lines(text, band='beginner'):
	"""Kembalikan (daftar dict soal valid, galat)."""
	rows, errors = [], []
	lines = [l for l in str(text or '').splitlines() if l.strip()]
	if len(lines) > MAX_LINES:
		errors.append(f'Maksimu liña {MAX_LINES} dala ida (ita iha {len(lines)}).')
		lines = lines[:MAX_LINES]
	for n, line in enumerate(lines, 1):
		parts = [p.strip() for p in line.split('|')]
		if len(parts) < 6:
			errors.append(f'Liña {n}: presiza "pergunta | A | B | C | D | resposta".')
			continue
		q, a, b, c, d, ans = parts[:6]
		expl = parts[6] if len(parts) > 6 else ''
		if not all((q, a, b, c, d)) or ans.lower() not in ('a', 'b', 'c', 'd'):
			errors.append(f'Liña {n}: resposta tenke a, b, c ka d, no opsaun hotu-hotu tenke iha.')
			continue
		if len(q) > 300 or max(len(a), len(b), len(c), len(d)) > 120 or len(expl) > 300:
			errors.append(f'Liña {n}: kompridu liu.')
			continue
		rows.append({'question': q, 'choice_a': a, 'choice_b': b, 'choice_c': c, 'choice_d': d,
                     'answer': ans.lower(), 'explanation_tet': expl, 'band': band})
	return rows, errors
