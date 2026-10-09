"""13 munisipiu Timor-Leste (12 munisipiu + Oecusse). `hckey` = hc-key pada peta Highcharts 'countries/tl/tl-all'.
`code` memakai kode ISO 3166-2:TL (dua huruf). Idempoten (kunci: hckey). Bisa diedit lewat Django admin."""

MUNICIPALITIES = [
    ('AL', 'Aileu', 'tl-al'), ('AN', 'Ainaro', 'tl-an'), ('BA', 'Baucau', 'tl-bc'), ('BO', 'Bobonaro', 'tl-bb'),
    ('CO', 'Cova Lima', 'tl-cl'), ('DI', 'Dili', 'tl-dl'), ('ER', 'Ermera', 'tl-er'), ('LA', 'Lautém', 'tl-bt'),
    ('LI', 'Liquiçá', 'tl-lq'), ('MT', 'Manatuto', 'tl-mt'), ('MF', 'Manufahi', 'tl-mf'),
    ('OE', 'Oecusse', 'tl-am'), ('VI', 'Viqueque', 'tl-vq'),
]


def run():
	from .models import Municipality
	for code, name, hckey in MUNICIPALITIES:
		Municipality.objects.update_or_create(hckey=hckey, defaults={'code': code, 'name': name})
	return len(MUNICIPALITIES)
