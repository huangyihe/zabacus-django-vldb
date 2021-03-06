# Generated by Django 2.1.2 on 2018-10-01 23:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bills', '0002_auto_20181001_2332'),
    ]

    operations = [
        migrations.AddField(
            model_name='billitem',
            name='paid_by',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='paid_items', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='billitem',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_items', to=settings.AUTH_USER_MODEL),
        ),
    ]
