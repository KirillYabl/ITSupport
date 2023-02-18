from textwrap import dedent

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from support_app.models import Order


def start_client(update: Update, context: CallbackContext) -> str:
    """Client start function which send a menu"""
    chat_id = update.effective_chat.id
    text = 'Здравствуйте, что вы хотите?'
    client = context.user_data['user'].client
    client_tariff = client.tariff

    keyboard = [
        [InlineKeyboardButton('Хочу оставить заявку', callback_data='create_order')],
        [InlineKeyboardButton('Связаться с подрядчиком', callback_data='send_message_to_contractor')],
    ]
    if client_tariff.can_see_contractor_contacts:
        keyboard.append(
            [
                InlineKeyboardButton(
                    'Хочу получить список подрядчиков, которые мне помогали',
                    callback_data='see_my_contractors'
                )
            ],
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    return 'HANDLE_MENU_CLIENT'


def handle_menu_client(update: Update, context: CallbackContext) -> str:
    chat_id = update.effective_chat.id
    query = update.callback_query
    client = context.user_data['user'].client

    message = 'Я вас не понял, нажмите одну из предложенных кнопок'  # answer when no one of if is True
    if query and query.data == 'create_order':  # client request order creation
        if not client.has_limit_of_orders():
            message = 'На вашем тарифе закончились заявки, вы можете купить повышенный тариф'
        elif client.has_active_order():
            message = 'Ваша заявка ещё в обработке, пожалуйста ожидайте'
        else:
            with open('order_examples.txt', 'r', encoding='UTF8') as file:  # TODO: сохранить при старте бота
                message = dedent('''
                Вы можете оставить заявку в чате в формате:
                - Сроки исполнения
                - Суть заказа
                - Что-нибудь еще

                Примеры заявок:
                ''')
                order_examples = file.readlines()
                for order_example in order_examples:
                    message += order_example
                context.bot.send_message(chat_id=chat_id, text=message)
            return 'WAITING_ORDER_TASK'
    elif query and query.data == 'send_message_to_contractor':  # client request send message to contractor
        message = 'У вас нет заказа взятого в работу'
        if client.has_in_work_order():
            message = 'Напишите сообщение подрядчику'
            context.bot.send_message(text=message, chat_id=chat_id)
            return 'WAIT_MESSAGE_TO_CONTRACTOR_CLIENT'
    elif query and query.data == 'see_my_contractors':  # client request to see his contractors
        message = 'На вашем тарифе нет такой функции, купите VIP тариф для подобной функции'
        if client.tariff.can_see_contractor_contacts:
            client_contractors = client.get_contractors()
            message = '\n'.join([f'@{contractor["contractor__tg_nick"]}' for contractor in client_contractors])

    context.bot.send_message(chat_id=chat_id, text=message)
    return start_client(update, context)


def wait_message_to_contractor_client(update: Update, context: CallbackContext) -> str:
    """Handler of waiting client message to contractor"""
    chat_id = update.effective_chat.id
    no_text_message = True
    if update.message:
        message_to_contractor = update.message.text
        no_text_message = False
    client = context.user_data['user'].client

    if not client.has_in_work_order() or no_text_message:  # if order disappeared or client send not a text
        message = 'Что-то пошло не так, попробуйте снова'
    else:
        order = client.get_in_work_order()

        # send message to contractor
        contractor_chat_id = order.contractor.telegram_id
        message_to_contractor = f'Вам сообщение от заказчика:\n\n{message_to_contractor}'
        context.bot.send_message(text=message_to_contractor, chat_id=contractor_chat_id)

        message = 'Сообщение успешно отправлено, когда подрядчик ответит вам придет уведомление'
    context.bot.send_message(text=message, chat_id=chat_id)

    return start_client(update, context)


def waiting_order_task(update: Update, context: CallbackContext) -> str:
    chat_id = update.effective_chat.id
    no_text_message = True
    if update.message:
        order_task = update.message.text
        no_text_message = False

    if no_text_message:
        message = 'Что-то пошло не так, попробуйте снова'
        context.bot.send_message(chat_id=chat_id, text=message)
        return 'WAITING_ORDER_TASK'
    else:
        context.user_data['creating_order_task'] = order_task
        message = 'Пришлите логин и пароль одним сообщением.\nПример:\nЛогин: Иван\nПароль: qwerty'
        context.bot.send_message(chat_id=chat_id, text=message)
        return 'WAITING_CREDENTIALS'


def waiting_credentials(update: Update, context: CallbackContext) -> str:
    chat_id = update.effective_chat.id
    no_text_message = True
    if update.message:
        credentials = update.message.text
        no_text_message = False
    client = context.user_data['user'].client

    if no_text_message:
        message = 'Что-то пошло не так, попробуйте снова'
        context.bot.send_message(chat_id=chat_id, text=message)
        return 'WAITING_CREDENTIALS'

    order_task = context.user_data.get('creating_order_task')
    if order_task is None:
        message = 'Упс, я потерял ваше задание, пришлите пожалуйста снова'
        context.bot.send_message(chat_id=chat_id, text=message)
        return 'WAITING_ORDER_TASK'
    else:
        hours = client.tariff.orders_limit // 60
        minutes = client.tariff.orders_limit % 60
        order = Order(task=order_task, client=client, creds=credentials)
        order.save()
        context.user_data['creating_order_task'] = None
        message = f'Спасибо! Ваш заказ успешно создан.\nЗаказ будет взят в течении {hours} ч. {minutes} мин.'
        context.bot.send_message(chat_id=chat_id, text=message)
        return start_client(update, context)


def start_not_found(update: Update, context: CallbackContext) -> str:
    """Unknown start function which send a menu"""
    chat_id = update.effective_chat.id
    message = 'Вы не являетесь нашим клиентом, пожалуйста обратитесь к менеджеру'
    context.bot.send_message(text=message, schat_id=chat_id)
    return 'START'