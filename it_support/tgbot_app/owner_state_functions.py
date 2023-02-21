import csv
import os
import random
import re
import time
from functools import partial
from typing import Any

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from support_app.models import Order
from support_app.models import BotUser
from support_app.models import Client
from support_app.models import Contractor
from support_app.models import Manager
from support_app.models import Owner
from support_app.models import Tariff


import logging

logger = logging.getLogger('tgbot_app_info')


def send_data_in_csv_file(update: Update, context: CallbackContext, filename: str, data_for_writing: list[list[str]]):
    """Save data in csv and send it."""
    logger.info('function "send_data_in_csv_file" was run')
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
            logger.info('function "send_data_in_csv_file" ended\n')
        except FileNotFoundError:
            pass


def process_bot_user_add(role_to_model: dict[BotUser.Role, dict[str, Any]], username: str, role: Client.Role) -> str:
    logger.info('function "process_bot_user_add" was run')
    message = []
    # check if this user not exists as active in all roles
    for model_role in role_to_model.keys():
        has_user_with_this_name = role_to_model[model_role]['model'].objects.active().filter(
            role__in=list(role_to_model.keys()),
            tg_nick=username,
        ).exists()
        if has_user_with_this_name:
            message.append(
                f'Уже есть активный пользователь с ролью "{role_to_model[role]["name"]}" с таким username'
            )

    # check username
    if not (5 <= len(username) <= 32):
        message.append('Длина имени пользователя должна быть от 5 до 32 символов')
    if not re.findall(BotUser.REGEX_TELEGRAM_NICKNAME, username):
        message.append('Username должен состоять из английских букв любого регистра, цифр и подчеркивания')

    if not message:
        # create user
        params = {
            'role': role,
            'status': BotUser.Status.active,
        }
        message = ['Пользователь успешно создан']
        if role == BotUser.Role.client:
            # client should have tariff

            # looking for easy tariff
            tariffs = Tariff.objects.exclude(name__startswith='test')
            params['tariff'] = tariffs.filter(
                can_reserve_contractor=False,
                can_see_contractor_contacts=False,
            ).first()
            if params['tariff'] is None:
                # looking for medium tariff
                params['tariff'] = tariffs.filter(can_reserve_contractor=False).first()
            if params['tariff'] is None:
                # looking for any tariff
                params['tariff'] = tariffs.first()
            params['paid'] = True
            message = ['Пользователь успешно создан с тарифом эконом по умолчанию']

        role_to_model[role]['model'].objects.get_or_create(tg_nick=username, defaults=params)
    message = '\n'.join(message)
    logger.info('function "process_bot_user_add" ended\n')
    return message


def process_bot_user(update: Update, context: CallbackContext, username: str, role: Client.Role, is_add: bool):
    """Process adding or create user with some role."""
    logger.info('function "process_bot_user" was run')
    chat_id = update.effective_chat.id
    role_to_model = {
        BotUser.Role.client: {
            'model': Client,
            'name': 'Клиент'
        },
        BotUser.Role.contractor: {
            'model': Contractor,
            'name': 'Подрядчик'
        },
        BotUser.Role.manager: {
            'model': Manager,
            'name': 'Менеджер'
        },
        BotUser.Role.owner: {
            'model': Owner,
            'name': 'Владелец'
        },
    }
    if username and username[0] == '@':
        username = username[1:]

    if is_add:
        message = process_bot_user_add(role_to_model, username, role)
    else:
        try:
            user = role_to_model[role]['model'].objects.get(tg_nick=username)
            user.status = BotUser.Status.inactive
            user.save()
            message = 'Пользователь успешно удален'
        except role_to_model[role]['model'].DoesNotExist:
            message = 'Пользователь с таким именем не найден'

    context.bot.send_message(text=message, chat_id=chat_id)
    logger.info('function "process_bot_user" ended\n')


def start_owner(update: Update, context: CallbackContext) -> str:
    """Owner start function which send a menu"""
    logger.info('function "start_owner" was run with the /start command')
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton('Биллинг подрядчиков за прошлый месяц', callback_data='contractor_billing_prev_month')],
        [InlineKeyboardButton('Статистика по заказам', callback_data='orders_stats')],
        [
            InlineKeyboardButton('Добавить клиента', callback_data='add_client'),
            InlineKeyboardButton('Удалить клиента', callback_data='delete_client'),
        ],
        [
            InlineKeyboardButton('Добавить подрядчика', callback_data='add_contractor'),
            InlineKeyboardButton('Удалить подрядчика', callback_data='delete_contractor'),
        ],
        [
            InlineKeyboardButton('Добавить менеджера', callback_data='add_manager'),
            InlineKeyboardButton('Удалить менеджера', callback_data='delete_manager'),
        ],
        [
            InlineKeyboardButton('Добавить владельца', callback_data='add_owner'),
            InlineKeyboardButton('Удалить владельца', callback_data='delete_owner'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(text='Что вас интересует', reply_markup=reply_markup, chat_id=chat_id)
    logger.info('function "start_owner" ended\n')
    return 'HANDLE_MENU_OWNER'


def handle_menu_owner(update: Update, context: CallbackContext) -> str:
    """Owner menu handler"""
    logger.info('function "handle_menu_owner" was run')
    chat_id = update.effective_chat.id
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton('Назад', callback_data='get_back')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query and query.data == 'contractor_billing_prev_month':  # owner request billing for pay to contractors
        header = ['Подрядчик', 'Выполненных заказов']
        billing = [
            [
                contractor_billing['contractor__tg_nick'],
                contractor_billing['count_orders'],
            ]
            for contractor_billing
            in Order.objects.calculate_billing()
        ]
        data_for_writing = [header] + billing
        filename = 'billing.csv'
        send_data_in_csv_file(update, context, filename, data_for_writing)
    elif query and query.data == 'orders_stats':  # owner request a stats of clients
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
        filename = 'stats.csv'
        send_data_in_csv_file(update, context, filename, data_for_writing)
    elif query:
        for role in ['client', 'contractor', 'manager', 'owner']:
            for action in ['add', 'delete']:
                if query.data == f'{action}_{role}':
                    message = f'Пришлите username. Пример: @{role}'
                    context.bot.send_message(text=message, chat_id=chat_id, reply_markup=reply_markup)
                    return f'WAITING_USERNAME_{role.upper()}_{action.upper()}'
    logger.info('function "handle_menu_owner" ended\n')
    return start_owner(update, context)


def waiting_username(update: Update, context: CallbackContext, role: Client.Role, is_add: bool) -> str:
    """Waiting username and call user process"""
    logger.info('function "waiting_username" was run')
    chat_id = update.effective_chat.id
    query = update.callback_query
    no_text_message = True
    if update.message:
        username = update.message.text
        no_text_message = False
    if query and query.data == 'get_back':
        return start_owner(update, context)
    elif no_text_message:  # if order disappeared or client send not a text
        message = 'Что-то пошло не так, попробуйте снова'
        context.bot.send_message(text=message, chat_id=chat_id)
    else:
        process_bot_user(update, context, username, role, is_add)
    logger.info('function "waiting_username" ended\n')
    return start_owner(update, context)


logger.info('"waiting_username" was run ')
waiting_username_client_add = partial(waiting_username, role=BotUser.Role.client, is_add=True)
waiting_username_contractor_add = partial(waiting_username, role=BotUser.Role.contractor, is_add=True)
waiting_username_manager_add = partial(waiting_username, role=BotUser.Role.manager, is_add=True)
waiting_username_owner_add = partial(waiting_username, role=BotUser.Role.owner, is_add=True)
waiting_username_client_delete = partial(waiting_username, role=BotUser.Role.client, is_add=False)
waiting_username_contractor_delete = partial(waiting_username, role=BotUser.Role.contractor, is_add=False)
waiting_username_manager_delete = partial(waiting_username, role=BotUser.Role.manager, is_add=False)
waiting_username_owner_delete = partial(waiting_username, role=BotUser.Role.owner, is_add=False)
logger.info('"waiting_username" ended\n')
