from django.db import migrations

ROLES = ['admin', 'staff', 'student']


def create_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in ROLES:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [migrations.RunPython(create_roles, migrations.RunPython.noop)]
