from django.core.validators import MinLengthValidator, RegexValidator, MinValueValidator
from django.db import models
from django.utils import timezone


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


class Contractor(BotUser):
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

    class Meta:
        verbose_name = 'тариф'
        verbose_name_plural = 'тарифы'

    def __str__(self):
        return f'Заказ {self.pk} ({self.status})'
