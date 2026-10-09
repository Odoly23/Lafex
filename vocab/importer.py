"""Import kosa kata massal: satu baris = 'tetun ; inglés ; contoh kalimat (opsional)'. Pemisah: ; | atau tab."""
import re

MAX_LINES = 200
SEP = re.compile(r'\s*[;|\t]\s*')


def parse_lines(text):
	"""Kembalikan (baris_valid, galat). Setiap baris valid: (tet, en, example_en)."""
	rows, errors = [], []
	lines = [l for l in str(text or '').splitlines() if l.strip()]
	if len(lines) > MAX_LINES:
		errors.append(f'Maksimu liña {MAX_LINES} dala ida (ita iha {len(lines)}).')
		lines = lines[:MAX_LINES]
	for n, line in enumerate(lines, 1):
		parts = [p.strip() for p in SEP.split(line.strip())]
		if len(parts) < 2 or not parts[0] or not parts[1]:
			errors.append(f'Liña {n}: presiza "tetun ; inglés".')
			continue
		tet, en, ex = parts[0], parts[1], (parts[2] if len(parts) > 2 else '')
		if len(tet) > 80 or len(en) > 80 or len(ex) > 200:
			errors.append(f'Liña {n}: kompridu liu.')
			continue
		rows.append((tet, en, ex))
	return rows, errors
