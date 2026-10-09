from django.db import migrations

# Harga awal (USD). Paket 1 bulan/1 tahun sengaja lebih murah per hari daripada paket mingguan.
PLANS = [
    ('1d', 'Loron 1', 24, '1.00', 1),
    ('3d', 'Loron 3', 24 * 3, '2.00', 2),
    ('7d', 'Loron 7', 24 * 7, '3.00', 3),
    ('30d', 'Fulan 1', 24 * 30, '8.00', 4),
    ('365d', 'Tinan 1', 24 * 365, '60.00', 5),
]


def seed(apps, schema_editor):
    Plan = apps.get_model('billing', 'Plan')
    for code, label, hours, price, sort in PLANS:
        Plan.objects.update_or_create(code=code, defaults={'label': label, 'hours': hours, 'price_usd': price, 'sort': sort})


class Migration(migrations.Migration):
    dependencies = [('billing', '0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
