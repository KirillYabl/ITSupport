from django.core.validators import MinLengthValidator, RegexValidator, MinValueValidator
from django.db import models
from django.db.transaction import atomic
from django.utils import timezone


class BotUserQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=BotUser.Status.active)


class BotUser(models.Model):
    class Role(models.TextChoices):
        client = 'Клиент'
        contractor = 'Подрядчик'
        manager = 'Менеджер'
        owner = 'Владелец'

    class Status(models.TextChoices):
        active = 'Активный'
        inactive = 'Неактивный'

    REGEX_TELEGRAM_NICKNAME = r'^\w{5,32}$'
    tg_nick = models.CharField(
        'ник в telegram',
        max_length=32,
        validators=[MinLengthValidator(5), RegexValidator(REGEX_TELEGRAM_NICKNAME)]
    )
    role = models.CharField('роль', max_length=30, choices=Role.choices)
    status = models.CharField('статус', max_length=30, choices=Status.choices, default=Status.active, db_index=True)
    telegram_id = models.IntegerField('telegram Id', db_index=True, blank=True, null=True)
    bot_state = models.CharField(
        'текущее состояния бота',
        max_length=100,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        'дата и время создания',
        default=timezone.now,
    )

    class Meta:
        verbose_name = 'пользователь бота'
        verbose_name_plural = 'пользователи бота'

    def __str__(self):
        return f'{self.role} {self.tg_nick} ({self.status})'


class Tariff(models.Model):
    name = models.CharField('название', max_length=50)
    orders_limit = models.PositiveSmallIntegerField(
        'максимальное число заявок в месяц',
        validators=[MinValueValidator(1)]
    )
    reaction_time_minutes = models.IntegerField(
        'время реакции на заявку в минутах',
        validators=[MinValueValidator(1)]
    )
    can_reserve_contractor = models.BooleanField('возможность закрепить подрядчика за собой')
    can_see_contractor_contacts = models.BooleanField('возможность увидеть контакты подрядчика')
    # TODO: отдельная таблица выставления счета за тариф клиенту
    price = models.DecimalField('цена', max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = 'тариф'
        verbose_name_plural = 'тарифы'

    def __str__(self):
        return self.name


class ClientQuerySet(models.QuerySet):
    def calculate_orders(self, year=None, month=None):
        # TODO: посчитать по каждому заказчику число заказов за месяц
        pass

    def get_contractors(self):
        return self.prefetch_related('orders').orders.values('contractor').distinct()


class Client(BotUser):
    tariff = models.ForeignKey(Tariff, related_name='clients', on_delete=models.DO_NOTHING)
    paid = models.BooleanField('оплачен ли тариф', db_index=True)

    def can_create_orders(self):
        return self.paid

    def has_limit_of_orders(self):
        try:
            billing_day = int(SystemSettings.objects.get('BILLING_DAY').parameter_value)
        except (SystemSettings.DoesNotExist, ValueError):
            billing_day = 1

        now = timezone.now()

        if billing_day <= now.day:
            min_date = timezone.datetime(now.year, now.month, now.day)
        else:
            before = now - timezone.timedelta(days=28)
            min_date = timezone.datetime(before.year, before.month, billing_day)

        created_orders_count = self.orders.filter(created_at__gte=min_date).count()
        can_create_orders_count = self.tariff.orders_limit

        return can_create_orders_count > created_orders_count

    def has_active_order(self):
        return self.orders.filter(status=Order.Status.in_work).count() > 0

    objects = ClientQuerySet.as_manager()

    class Meta:
        verbose_name = 'клиент'
        verbose_name_plural = 'клиенты'

    def __str__(self):
        return f'{self.tg_nick} ({self.status})'


class ContractorQuerySet(models.QuerySet):
    def get_available(self):
        not_available_contractors = Order.objects.select_related('contractor').filter(
            status=Order.Status.in_work).values('contractor').distinct()
        not_available_contractor_ids = [contractor.id for contractor in not_available_contractors]
        return self.exclude(id__in=not_available_contractor_ids)


class Contractor(BotUser):
    objects = ContractorQuerySet.as_manager()

    def delete_from_bot(self):
        contractor_orders = Order.objects.filter(status=Order.Status.in_work, contractor=self)
        with atomic():
            contractor_orders.update(
                status=Order.Status.created,
                assigned_at=None,
                contractor=None,
                not_in_work_manager_informed=False,
                late_work_manager_informed=False,
                in_work_client_informed=False,
            )
            self.status = BotUser.Status.inactive
            self.save()

    class Meta:
        verbose_name = 'подрядчик'
        verbose_name_plural = 'подрядчики'

    def __str__(self):
        return f'{self.tg_nick} ({self.status})'


class Manager(BotUser):
    class Meta:
        verbose_name = 'менеджер'
        verbose_name_plural = 'менеджеры'

    def __str__(self):
        return f'{self.tg_nick} ({self.status})'


class Owner(BotUser):
    class Meta:
        verbose_name = 'владелец'
        verbose_name_plural = 'владельцы'

    def __str__(self):
        return f'{self.tg_nick} ({self.status})'


class OrderQuerySet(models.QuerySet):
    def get_warning_orders_not_in_work(self):
        orders_not_in_work = self.objects.select_related('client').filter(
            status=self.Status.created,
            not_in_work_manager_informed=False,
        )
        warning_orders = []
        tariffs = Tariff.objects.all()

        # TODO: написать через аннотейты
        for tariff in tariffs:
            tariff_orders = orders_not_in_work.filter(client__tariff=tariff)
            for tariff_order in tariff_orders:
                not_in_work_time = tariff_order.created_at - timezone.now()
                limit = 0.95
                tariff_limit_seconds = tariff.reaction_time_minutes * 60
                if not_in_work_time.total_seconds() / tariff_limit_seconds > limit:
                    warning_orders.append(tariff_order)
        return warning_orders

    def get_warning_orders_not_closed(self):
        orders_not_closed = self.objects.select_related('client', 'contractor').filter(
            status=self.Status.in_work,
            late_work_manager_informed=False,
        )
        warning_orders = []

        for order in orders_not_closed:
            not_closed_time = order.assigned_at - timezone.now()
            limit_seconds = 60 * 60 * 24  # TODO: добавить эстимейты
            limit = 0.95
            if not_closed_time.total_seconds() / limit_seconds > limit:
                warning_orders.append(order)
        return warning_orders

    def get_available(self):
        return self.filter(status=Order.Status.created)

    def get_in_work_not_informed(self):
        return self.filter(status=Order.Status.in_work, in_work_client_informed=False)

    def get_closed_not_informed(self):
        return self.filter(status=Order.Status.closed, closed_client_informed=False)

    def calculate_average_orders_in_month(self, year=None, month=None):
        # TODO: посчитать сколько в среднем делается заказов в день в течении месяца с точностью до тарифа
        pass


class Order(models.Model):
    class Status(models.TextChoices):
        created = 'создан'
        in_work = 'в работе'
        closed = 'закрыт'
        cancelled = 'отменен'

    task = models.TextField('задание')
    client = models.ForeignKey(Client, related_name='orders', on_delete=models.DO_NOTHING)
    contractor = models.ForeignKey(
        Contractor,
        related_name='orders',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        'дата и время создания',
        default=timezone.now,
        db_index=True,
    )
    assigned_at = models.DateTimeField(
        'дата и время взятия в работу',
        null=True,
        blank=True,
        db_index=True,
    )
    closed_at = models.DateTimeField(
        'дата и время выполнения',
        null=True,
        blank=True,
        db_index=True,
    )
    status = models.CharField(
        'статус',
        max_length=30,
        choices=Status.choices,
        default=Status.created,
        db_index=True,
    )

    not_in_work_manager_informed = models.BooleanField(
        'менеджер проинформирован что заказ не взят',
        default=False,
    )
    late_work_manager_informed = models.BooleanField(
        'менеджер проинформирован что заказ долго выполняется',
        default=False,
    )
    in_work_client_informed = models.BooleanField(
        'клиент проинформирован что заказ взят',
        default=False,
    )
    closed_client_informed = models.BooleanField(
        'клиент проинформирован что заказ выполнен',
        default=False,
    )

    objects = OrderQuerySet.as_manager()

    def take_in_work(self, contractor):
        with atomic():
            self.contractor = contractor
            self.assigned_at = timezone.now()
            self.status = self.Status.in_work
            self.save()

    def close_work(self):
        with atomic():
            self.closed_at = timezone.now()
            self.status = self.Status.closed
            self.save()

    def cancel_work(self):
        with atomic():
            self.closed_at = timezone.now()
            self.status = self.Status.cancelled
            self.save()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'Заказ {self.pk} ({self.status})'


class SystemSettings(models.Model):
    parameter_name = models.CharField(
        'имя системного параметра',
        max_length=100,
        help_text='желательно задавать на английском и без пробелов',
    )
    parameter_value = models.TextField(
        'значение системного параметра',
        blank=True,
        help_text='может быть пустой строкой, тогда метод которому это нужно сам придумает дефолт',
    )
    description = models.TextField('описание параметра')
