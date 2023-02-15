from typing import Callable

from django.db.models import Q
from django.db.transaction import atomic
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater
)
from telegram.error import TelegramError

from support_app.models import BotUser
from support_app.models import Contractor
from support_app.models import Client
from support_app.models import Manager
from support_app.models import Order

from telegram.utils import request


def get_user(func):
    def wrapper(update, context):
        chat_id = update.effective_chat.id
        username = update.effective_user.username

        try:
            user = BotUser.objects.get(Q(tg_nick=username) | Q(telegram_id=chat_id))
        except BotUser.DoesNotExist:
            user = None

        context.user_data['user'] = user
        return func(update, context)

    return wrapper


class TgBot(object):

    def __init__(self, tg_token: str, states_functions: dict[str, dict[str, Callable]]) -> None:
        self.tg_token = tg_token
        self.states_functions = states_functions
        self.updater = Updater(token=tg_token, use_context=True)
        self.updater.dispatcher.add_handler(CommandHandler('start', get_user(self.handle_users_reply)))
        self.updater.dispatcher.add_handler(CommandHandler('help', self.help_handler))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(get_user(self.handle_users_reply)))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, get_user(self.handle_users_reply)))
        self.updater.dispatcher.add_error_handler(self.error)
        self.job_queue = self.updater.job_queue

        self.job_queue.run_repeating(
            self.handle_warning_orders_not_in_work,
            interval=60,
            first=10,
            name='handle_warning_orders_not_in_work'
        )

        self.job_queue.run_repeating(
            self.handle_warning_orders_not_closed,
            interval=60,
            first=20,
            name='handle_warning_orders_not_closed'
        )

    def handle_users_reply(self, update, context):
        user = context.user_data['user']

        if user is None:
            self.states_functions['unknown']['start'](update, context)
            return

        if update.message:
            user_reply = update.message.text
        elif update.callback_query:
            user_reply = update.callback_query.data
        else:
            return

        chat_id = update.effective_chat.id

        if user_reply == '/start':
            user_state = 'START'
        else:
            user_state = user.bot_state
            user_state = user_state if user_state else 'START'

        state_handler = self.states_functions[user.role][user_state]
        next_state = state_handler(update, context)
        user.bot_state = next_state
        user.save()

    def error(self, update, context):
        print(f'Update "{update}" caused error "{context.error}"')
        raise context.error

    def help_handler(self, update, context):
        update.message.reply_text("Используйте /start для того, что бы перезапустить бот")

    def handle_warning_orders_not_in_work(self, context):
        """
        Каждому менеджеру отправить сообщение по каждому не взятому заказу
        В сообщении указать задачу (поле task у заказа) и контакты заказчика (поле client.tg_nick у заказа) не забыв добавить @
        """
        warning_orders_not_in_work = Order.objects.get_warning_orders_not_in_work()
        managers = Manager.objects.active()

        warning_orders_not_in_work.update(not_in_work_manager_informed=True)  # это в конце вызывается

    def handle_warning_orders_not_closed(self, context):
        """
        Каждому менеджеру отправить сообщение по каждому не выполненному заказу
        В сообщении указать задачу (поле task у заказа) и
        контакты заказчика (поле client.tg_nick у заказа) и
        подрядчика (поле contractor.tg_nick у заказа) не забыв добавить @
        """
        warning_orders_not_closed = Order.objects.get_warning_orders_not_closed()
        managers = Manager.objects.active()

        warning_orders_not_closed.update(late_work_manager_informed=True)  # это в конце вызывается


def start_not_found(update, context):
    """Ответ для неизвестного, что мы его не знаем ему нужно связаться с админами"""
    return 'START'


# Функции для менеджера
def start_manager(update, context):
    """Ответ для менеджера с кнопками (пока одна)"""
    return 'HANDLE_CONTACTS'


def handle_contacts(update, context):
    """
    Из модели подрядчика и заказа достать всех подрядчиков, у которых нет активных заказов.
    Ответить списком их имен телеграм (в БД они хранятся без @, нужно добавить).
    Проверить, что менеджер нажал кнопку
    Если не нажал, то сообщить что неизвестный ввод, но все равно вернуть на старт
    """
    available_contractors = Contractor.objects.get_available()  # список доступных подрядчиков
    # по свойству tg_nick лежат их имена
    return start_manager(update, context)


# Функции для клиента
def start_client(update, context):
    """Ответ для клиента"""
    return ''  # TODO: придумать название


# Функции для подрядчика
def start_contractor(update, context):
    """Ответ для подрядчика"""
    return ''  # TODO: придумать название
