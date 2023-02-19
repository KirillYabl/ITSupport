import csv
import os
import random
import time

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from support_app.models import Order


def send_data_in_csv_file(update: Update, context: CallbackContext, filename: str, data_for_writing: list[list[str]]):
    """Save data in csv and send it."""
    os_filename = f'{time.time()}_{random.randint(1, 2 ** 20)}_{filename}'
    chat_id = update.effective_chat.id
    try:
        with open(os_filename, 'w', newline='', encoding='utf8') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerows(data_for_writing)
        with open(os_filename, 'rb') as f:
            context.bot.send_document(document=f, filename=filename, chat_id=chat_id)
    finally:
        try:
            os.remove(os_filename)
        except FileNotFoundError:
            pass


def start_owner(update: Update, context: CallbackContext) -> str:
    """Owner start function which send a menu"""
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton('Биллинг подрядчиков за прошлый месяц', callback_data='contractor_billing_prev_month')],
        [InlineKeyboardButton('Статистика по заказам', callback_data='orders_stats')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(text='Что вас интересует', reply_markup=reply_markup, chat_id=chat_id)
    return 'HANDLE_MENU_OWNER'


def handle_menu_owner(update: Update, context: CallbackContext) -> str:
    """Owner menu handler"""
    chat_id = update.effective_chat.id
    query = update.callback_query

    message = 'Я вас не понял, нажмите одну из предложенных кнопок'
    if query and query.data == 'contractor_billing_prev_month':  # owner request billing for pay to contractors
        header = ['Подрядчик', 'Выполненных заказов']
        billing = [
            [
                contractor_billing["contractor__tg_nick"],
                contractor_billing["count_orders"],
            ]
            for contractor_billing
            in Order.objects.calculate_billing()
        ]
        data_for_writing = [header] + billing
        filename = f'billing.csv'
        send_data_in_csv_file(update, context, filename, data_for_writing)
    elif query and query.data.startswith('orders_stats'):  # owner request a stats of clients
        header = ['Начало биллинга', 'Клиент', 'Число заказов']
        billing_start_index = 0
        client_name_index = 1
        orders_count_index = 2
        clients_months_stats = [
            [
                client_month_stat[billing_start_index],
                client_month_stat[client_name_index],
                client_month_stat[orders_count_index],
            ]
            for client_month_stat
            in Order.objects.calculate_average_orders_in_month()
        ]
        data_for_writing = [header] + clients_months_stats
        filename = f'stats.csv'
        send_data_in_csv_file(update, context, filename, data_for_writing)

    return start_owner(update, context)
