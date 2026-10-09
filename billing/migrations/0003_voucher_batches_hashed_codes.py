import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def hash_existing_codes(apps, schema_editor):
    """Voucher lama (kode tersimpan polos) -> simpan hash saja, beri nomor seri LEG-xxxxxx."""
    from billing import vouchers
    Voucher = apps.get_model('billing', 'Voucher')
    for v in Voucher.objects.all():
        v.code_hash = vouchers.hash_code(v.code)
        v.serial = f'LEG-{v.pk:06d}'
        v.save(update_fields=['code_hash', 'serial'])


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_seed_plans'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VoucherBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=80, verbose_name='Toko / penjual (label)')),
                ('quantity', models.PositiveIntegerField(verbose_name='Kuantidade')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Data kria')),
                ('valid_until', models.DateTimeField(verbose_name="Válidu to'o")),
                ('voided_at', models.DateTimeField(blank=True, null=True, verbose_name='Kansela iha')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Kria husi')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='billing.plan', verbose_name='Pakote')),
            ],
            options={'verbose_name': 'Batch vaucher', 'verbose_name_plural': 'Batch vaucher', 'ordering': ['-created_at']},
        ),
        migrations.AddField(model_name='voucher', name='batch', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='vouchers', to='billing.voucherbatch', verbose_name='Batch')),
        migrations.AddField(model_name='voucher', name='serial', field=models.CharField(max_length=24, null=True, verbose_name='Nu. seri')),
        migrations.AddField(model_name='voucher', name='code_hash', field=models.CharField(max_length=64, null=True)),
        migrations.AddField(model_name='voucher', name='voided_at', field=models.DateTimeField(blank=True, null=True, verbose_name='Kansela iha')),
        migrations.RunPython(hash_existing_codes, migrations.RunPython.noop),
        migrations.RemoveField(model_name='voucher', name='code'),
        migrations.AlterField(model_name='voucher', name='serial', field=models.CharField(max_length=24, unique=True, verbose_name='Nu. seri')),
        migrations.AlterField(model_name='voucher', name='code_hash', field=models.CharField(max_length=64, unique=True)),
        migrations.CreateModel(
            name='RedeemAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.CharField(blank=True, max_length=45)),
                ('ok', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
