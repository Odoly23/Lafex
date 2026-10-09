"""Penilaian pronunciation dari hasil pengenalan suara (speech-to-text).

PENTING (batas yang jujur): ini mengukur apa yang berhasil dipahami oleh pengenal suara di perangkat siswa,
yaitu kata mana yang terdengar sesuai kalimat target. Ini BUKAN penilaian fonem seperti penilai profesional,
dan tidak mendengar rekaman suara. Cukup untuk latihan dan menandai siswa yang perlu dibantu."""
import difflib
import re

CREDIT = {'ok': 1.0, 'close': 0.6, 'missed': 0.0}
CLOSE_RATIO = 0.75


def words(text):
	text = str(text or '').lower().replace('’', "'")
	return re.findall(r"[a-z0-9']+", text)


def score_phrase(expected, heard, confidence=None):
	exp, hrd = words(expected), words(heard)
	if not exp:
		return {'score': 0, 'detail': [], 'heard': ' '.join(hrd)}
	status = ['missed'] * len(exp)
	heard_for = [''] * len(exp)
	sm = difflib.SequenceMatcher(a=exp, b=hrd, autojunk=False)
	for tag, i1, i2, j1, j2 in sm.get_opcodes():
		if tag == 'equal':
			for k in range(i1, i2):
				status[k], heard_for[k] = 'ok', exp[k]
		elif tag == 'replace':
			for k in range(i1, i2):
				j = j1 + (k - i1)
				if j < j2:  # kata diganti: mirip = 'close'
					heard_for[k] = hrd[j]
					if difflib.SequenceMatcher(None, exp[k], hrd[j]).ratio() >= CLOSE_RATIO:
						status[k] = 'close'
	accuracy = sum(CREDIT[s] for s in status) / len(exp)
	extra = max(0, len(hrd) - len(exp))
	extra_factor = max(0.7, 1 - 0.1 * extra)  # kata berlebih sedikit mengurangi nilai
	conf_factor = 1.0
	if confidence is not None:
		try:
			conf_factor = 0.75 + 0.25 * min(1.0, max(0.0, float(confidence)))
		except (TypeError, ValueError):
			pass
	score = round(100 * accuracy * extra_factor * conf_factor)
	return {
        'score': max(0, min(100, score)),
        'detail': [{'word': w, 'status': s, 'heard': h} for w, s, h in zip(exp, status, heard_for)],
        'heard': ' '.join(hrd),
    }
