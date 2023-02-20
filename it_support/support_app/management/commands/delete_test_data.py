from django.core.management.base import BaseCommand

from support_app.models import Order
from support_app.models import Client
from support_app.models import Manager
from support_app.models import Contractor
from support_app.models import Tariff


class Command(BaseCommand):
    help = "Create test orders"

    def handle(self, *args, **kwargs):
        Order.objects.filter(task__startswith='test').delete()
        Client.objects.filter(tg_nick__startswith='test').delete()
        Manager.objects.filter(tg_nick__startswith='test').delete()
        Contractor.objects.filter(tg_nick__startswith='test').delete()
        Tariff.objects.filter(name__startswith='test').delete()
