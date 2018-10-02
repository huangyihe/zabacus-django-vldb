# Generated by Django 2.1.2 on 2018-10-01 23:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import zabacus.bills.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('date', models.DateTimeField()),
                ('edited', models.DateTimeField()),
                ('status', models.CharField(choices=[(zabacus.bills.models.BillStatus('open'), 'open'), (zabacus.bills.models.BillStatus('settled'), 'settled'), (zabacus.bills.models.BillStatus('dispute'), 'dispute')], max_length=32)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BillItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('desc', models.TextField()),
                ('date', models.DateTimeField()),
                ('edited', models.DateTimeField()),
                ('total', models.FloatField()),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bills.Bill')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Involvement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bills.Bill')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ItemWeightAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField()),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bills.BillItem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='bill',
            name='people',
            field=models.ManyToManyField(related_name='invloved', through='bills.Involvement', to=settings.AUTH_USER_MODEL),
        ),
    ]
