import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from support_app.models import Order
from support_app.models import BotUser
from support_app.models import Client
from support_app.models import Manager
from support_app.models import Contractor
from support_app.models import Tariff


class Command(BaseCommand):
    help = "Create test orders"

    def handle(self, *args, **kwargs):
        tariff_1 = Tariff(
            name='test1',
            orders_limit=5,
            reaction_time_minutes=1440,
            can_reserve_contractor=False,
            can_see_contractor_contacts=False,
            price=Decimal(4000)
        )
        tariff_2 = Tariff(
            name='test2',
            orders_limit=15,
            reaction_time_minutes=1440,
            can_reserve_contractor=False,
            can_see_contractor_contacts=False,
            price=Decimal(10000)
        )
        tariff_3 = Tariff(
            name='test3',
            orders_limit=50,
            reaction_time_minutes=60,
            can_reserve_contractor=True,
            can_see_contractor_contacts=True,
            price=Decimal(25000)
        )
        tariff_1.save()
        tariff_2.save()
        tariff_3.save()

        for i in range(10):
            client = Client(
                tg_nick=f'testclient{i}',
                role=BotUser.Role.client,
                status=BotUser.Status.active if i != 1 else BotUser.Status.inactive,
                tariff=random.choice([tariff_1, tariff_2, tariff_3]),
                paid=True if i != 0 else False,
            )
            manager = Manager(
                tg_nick=f'testmanager{i}',
                role=BotUser.Role.manager,
                status=BotUser.Status.active if i != 1 else BotUser.Status.inactive,
            )
            contractor = Contractor(
                tg_nick=f'testcontractor{i}',
                role=BotUser.Role.contractor,
                status=BotUser.Status.active if i != 1 else BotUser.Status.inactive,
            )
            client.save()
            manager.save()
            contractor.save()
        clients = Client.objects.filter(tg_nick__startswith='test')
        contractors = Contractor.objects.filter(tg_nick__startswith='test')

        now = timezone.now()
        created_at = now - timezone.timedelta(days=200)
        assigned_at = created_at + timezone.timedelta(minutes=random.randint(1, 1440))
        closed_at = assigned_at + timezone.timedelta(minutes=random.randint(1, 1440))
        task_number = 0
        while closed_at < now:
            order = Order(
                task=f'testtask{task_number}',
                client=random.choice(clients),
                contractor=random.choice(contractors),
                created_at=created_at,
                assigned_at=assigned_at,
                closed_at=closed_at,
                status=Order.Status.closed,
                in_work_client_informed=True,
                closed_client_informed=True,
                creds=f'testcreds{task_number}',
                estimated_hours=random.randint(1, 24),
            )
            order.save()
            created_at = created_at + timezone.timedelta(minutes=random.randint(1, 1440))
            assigned_at = created_at + timezone.timedelta(minutes=random.randint(1, 1440))
            closed_at = assigned_at + timezone.timedelta(minutes=random.randint(1, 1440))
