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
    status = models.CharField('статус', max_length=30, choices=Status.choices, db_index=True)
    telegram_id = models.IntegerField('telegram Id', db_index=True, blank=True, null=True)
    bot_state = models.CharField(
        'текущее состояния бота',
        max_length=100,
        null=True,
        blank=True,
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

    class Meta:
        verbose_name = 'тариф'
        verbose_name_plural = 'тарифы'

    def __str__(self):
        return self.name


class Client(BotUser):
    tariff = models.ForeignKey(Tariff, related_name='clients', on_delete=models.DO_NOTHING)
    paid = models.BooleanField('оплачен ли тариф', db_index=True)

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

    def get_warning_orders_not_in_work(self):
        orders_not_in_work = self.objects.select_related('client').filter(
            status=self.Status.created,
            not_in_work_manager_informed=False,
        )
        warning_orders = []
        tariffs = Tariff.objects.all()

        for tariff in tariffs:
            tariff_orders = orders_not_in_work.filter(client__tariff=tariff)
            for tariff_order in tariff_orders:
                not_in_work_time = tariff_order.created_at - timezone.now()
                limit = 0.95
                tariff_limit_seconds = tariff.reaction_time_minutes * 60
                if not_in_work_time.total_seconds() / tariff_limit_seconds > limit:
                    warning_orders.append(tariff_order)
        return warning_orders

    class Meta:
        verbose_name = 'тариф'
        verbose_name_plural = 'тарифы'

    def __str__(self):
        return f'Заказ {self.pk} ({self.status})'
