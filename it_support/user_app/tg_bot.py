
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater
    )
from telegram.error import TelegramError

# from .models import User


# def get_user(func):
#     def wrapper(update, context):
#         chat_id = update.message.chat_id
#         user, _ = User.objects.get_or_create(telegram_id=chat_id)
#         context.user_data['user'] = user
#         return func(update, context)
#     return wrapper


class TgBot(object):

    def __init__(self, tg_token, states_functions):
        self.tg_token = tg_token
        self.states_functions = states_functions
        self.updater = Updater(token=tg_token, use_context=True)
        self.updater.dispatcher.add_handler(CommandHandler('start', self.start))
        self.updater.dispatcher.add_handler(CommandHandler('help', self.help_handler))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.handle_users_reply))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text, self.handle_users_reply))
        self.updater.dispatcher.add_error_handler(self.error)
        self.job_queue = self.updater.job_queue

    def handle_users_reply(self, update, context):
        if update.message:
            state_handler = self.states_functions['echo']
            next_state = state_handler(update, context)

    def start(self, update, context):
        update.message.reply_text('Здравствуйте, чем могу вам помочь?')

    def error(self, update, context):
        raise TelegramError

    def help_handler(self, update, context):
        update.message.reply_text("Используйте /start для того, что бы перезапустить бот")


def echo(update, context):
    update.message.reply_text(update.message.text)
