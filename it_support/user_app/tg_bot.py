from typing import Callable

from django.db.models import Q
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
        chat_id = update.message.chat_id
        username = update.message.username

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

    def handle_users_reply(self, update, context):
        user = context.user_data['user']

        if user is None:
            self.states_functions['unknown']['start'](update, context)
            return

        if update.message:
            user_reply = update.message.text
            chat_id = update.message.chat_id
        elif update.callback_query:
            user_reply = update.callback_query.data
            chat_id = update.callback_query.message.chat_id
        else:
            return

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
        raise TelegramError

    def help_handler(self, update, context):
        update.message.reply_text("Используйте /start для того, что бы перезапустить бот")


def start_not_found(update, context):
    """Ответ для неизвестного, что мы его не знаем ему нужно связаться с админами"""
    return 'START'


def start_manager(update, context):
    """Ответ для менеджера"""
    return 'HANDLE_CONTACTS'


def start_client(update, context):
    """Ответ для клиента"""
    return ''  # TODO: придумать название


def start_contractor(update, context):
    """Ответ для подрядчика"""
    return ''  # TODO: придумать название
