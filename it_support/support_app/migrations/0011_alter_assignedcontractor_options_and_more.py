# Generated by Django 4.1.7 on 2023-02-19 14:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('support_app', '0010_remove_order_closed_client_informed_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='assignedcontractor',
            options={'verbose_name': 'закрепленный подрядчик', 'verbose_name_plural': 'закрепленные подрядчики'},
        ),
        migrations.AlterModelOptions(
            name='systemsettings',
            options={'verbose_name': 'системный параметр', 'verbose_name_plural': 'системные параметры'},
        ),
    ]