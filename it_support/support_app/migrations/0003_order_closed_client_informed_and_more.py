# Generated by Django 4.1.7 on 2023-02-15 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support_app', '0002_botuser_bot_state_botuser_telegram_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='closed_client_informed',
            field=models.BooleanField(default=False, verbose_name='клиент проинформирован что заказ выполнен'),
        ),
        migrations.AddField(
            model_name='order',
            name='in_work_client_informed',
            field=models.BooleanField(default=False, verbose_name='клиент проинформирован что заказ взят'),
        ),
        migrations.AddField(
            model_name='order',
            name='late_work_manager_informed',
            field=models.BooleanField(default=False, verbose_name='менеджер проинформирован что заказ долго выполняется'),
        ),
        migrations.AddField(
            model_name='order',
            name='not_in_work_manager_informed',
            field=models.BooleanField(default=False, verbose_name='менеджер проинформирован что заказ не взят'),
        ),
    ]
