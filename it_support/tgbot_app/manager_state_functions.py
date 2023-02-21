from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from support_app.models import Contractor

import logging

logger = logging.getLogger('tgbot_app_info')


def start_manager(update: Update, context: CallbackContext) -> str:
    """Manager start function which send a menu"""
    logger.info('function "start_manager" was run with the /start command')
    keyboard = [
        [InlineKeyboardButton('Контакты доступных подрядчиков', callback_data='contacts_available_contractors')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id
    context.bot.send_message(text='Что вас интересует', reply_markup=reply_markup, chat_id=chat_id)
    logger.info('function "start_manager" ended\n')
    return 'HANDLE_MENU_MANAGER'


def handle_menu_manager(update: Update, context: CallbackContext) -> str:
    """Manager menu handler, also answer if unknown enter"""
    logger.info('function "handle_menu_manager" was run')
    chat_id = update.effective_chat.id
    query = update.callback_query

    message = 'Я вас не понял, выберите из предложенных кнопок'
    if query and query.data == 'contacts_available_contractors':
        available_contractors = Contractor.objects.get_available()
        message = '\n'.join([f'@{contractor.tg_nick}' for contractor in available_contractors])

    context.bot.send_message(text=message, chat_id=chat_id)
    logger.info('function "handle_menu_manager" ended\n')
    return start_manager(update, context)
