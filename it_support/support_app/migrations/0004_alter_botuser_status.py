# Generated by Django 4.1.7 on 2023-02-15 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support_app', '0003_order_closed_client_informed_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='botuser',
            name='status',
            field=models.CharField(choices=[('Активный', 'Active'), ('Неактивный', 'Inactive')], db_index=True, default='Активный', max_length=30, verbose_name='статус'),
        ),
    ]
