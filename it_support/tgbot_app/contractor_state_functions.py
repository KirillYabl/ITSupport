from textwrap import dedent

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from support_app.models import Order
from support_app.models import SystemSettings
from support_app.models import Contractor


def start_contractor(update: Update, context: CallbackContext) -> str:
    """Contractor start function which send a menu"""
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton('Как это работает?', callback_data='how_contractor_bot_work')],
        [InlineKeyboardButton('Посмотреть заказы', callback_data='watch_orders')],
        [InlineKeyboardButton('Написать заказчику', callback_data='send_message_to_client')],
        [InlineKeyboardButton('Завершить заказ', callback_data='close_order')],
        [InlineKeyboardButton('Мой заработок за месяц', callback_data='my_salary')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(text='Выберите действие', reply_markup=reply_markup, chat_id=chat_id)
    return 'HANDLE_MENU_CONTRACTOR'


def handle_watch_orders_callback(
        update: Update,
        context: CallbackContext,
        chat_id: str,
) -> tuple[bool, str, str]:
    """
    Handling watch orders callbacks.

    Return bool means return or not and what return and also message if not return
    """
    available_orders = list(Order.objects.get_available())
    if not available_orders:
        message = 'Нет заказов, которые можно взять в работу'
        context.bot.send_message(text=message, chat_id=chat_id)
        return True, start_contractor(update, context), ''
    for i, order in enumerate(available_orders):
        # send every order in different message because it contains button to take order
        message = dedent(f'''
                Задание:
                {order.task}
                ''')
        keyboard = [
            [InlineKeyboardButton('Взять в работу', callback_data=f'take_order|{order.pk}')],
        ]
        if i == len(available_orders) - 1:
            keyboard.append([InlineKeyboardButton('Вернуться назад', callback_data='get_back')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(text=message, reply_markup=reply_markup, chat_id=chat_id)
    return True, 'HANDLE_MENU_CONTRACTOR', ''


def handle_send_message_to_client_callback(
        context: CallbackContext,
        contractor: Contractor,
        chat_id: str,
) -> tuple[bool, str, str]:
    """
    Handling send message to client callbacks.

    Return bool means return or not and what return and also message if not return
    """
    message = 'У вас нет активного заказа'
    if contractor.has_order_in_work():
        message = 'Напишите сообщение клиенту'
        keyboard = [
            [InlineKeyboardButton('Вернуться назад', callback_data='get_back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(text=message, chat_id=chat_id, reply_markup=reply_markup)
        return True, 'WAIT_MESSAGE_TO_CLIENT_CONTRACTOR', ''
    return False, '', message


def handle_take_order_callback(
        update: Update,
        context: CallbackContext,
        contractor: Contractor,
        chat_id: str,
) -> tuple[bool, str, str]:
    """
    Handling take order callbacks.

    Return bool means return or not and what return and also message if not return
    """
    order_pk = update.callback_query.data.split('|')[-1]
    bad_scenario = False

    if contractor.has_order_in_work():
        # it unnature limit, because now messages and close work not support many orders
        message = 'У вас уже есть активный заказ в работе'
        # fast send message and return for not spend time in checks below
        context.bot.send_message(text=message, chat_id=chat_id)
        return True, start_contractor(update, context), ''

    # check if order exist
    try:
        order = Order.objects.get(pk=int(order_pk))
    except (Order.DoesNotExist, ValueError):
        order = None
        message = 'Что-то пошло не так, заказ не найден, попробуйте снова получить список заказов'
        bad_scenario = True

    # check if not blocked by another contractor
    if order is not None and order.status != Order.Status.created:
        message = 'К сожалению заказ уже взяли, попробуйте снова получить список заказов'
        bad_scenario = True

    if not bad_scenario:
        message = dedent('''
                Пришлите приблизительную оценку требуемого на выполнения времени в часах
                Оценка от 1 до 24 часов, если вы считаете, что заказ потребует больше времени
                обратитесь к менеджерам, мы не оказываем проектную поддержку
                ''')
        context.user_data['order_in_process'] = order
        keyboard = [
            [InlineKeyboardButton('Вернуться в начало', callback_data='return_to_start')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(text=message, chat_id=chat_id, reply_markup=reply_markup)
        return True, 'WAIT_ESTIMATE_CONTRACTOR', ''
    return False, '', message


def handle_close_order_callback(
        context: CallbackContext,
        contractor: Contractor,
) -> tuple[bool, str, str]:
    """
    Handling close order callbacks.

    Return bool means return or not and what return and also message if not return
    """
    message = 'У вас нет активного заказа'
    if contractor.has_order_in_work():
        order_in_work = contractor.get_order_in_work()
        client_chat_id = order_in_work.client.telegram_id
        order_in_work.close_work()
        # also notify client
        message_to_client = dedent('''
                Подрядчик выполнил ваш заказ, делаем успехов в вашем бизнесе!
                Если вам нужна будет помощь, мы рядом!
                ''')
        if order_in_work.client.tariff.can_reserve_contractor:
            message_to_client += 'Вы можете закрепить последнего подрядчика.'
        context.bot.send_message(text=message_to_client, chat_id=client_chat_id)
        message = 'Спасибо за вашу работу! Теперь вы можете брать новый заказ'
    return False, '', message


def handle_my_salary_callback(contractor: Contractor) -> tuple[bool, str, str]:
    """
    Handling my salary callbacks.

    Return bool means return or not and what return and also message if not return
    """
    closed_orders_count = contractor.get_closed_in_actual_billing_orders().count()
    try:
        order_rate = int(SystemSettings.objects.get(
            'ORDER_RATE'
        ).parameter_value)
    except (SystemSettings.DoesNotExist, ValueError):
        order_rate = 500
    salary = closed_orders_count * order_rate
    message = f'Выполнено заказав в отчетном периоде: {closed_orders_count}. К выплате {salary} руб.'
    return False, '', message


def handle_menu_contractor(update: Update, context: CallbackContext) -> str:
    """Manager menu handler"""
    chat_id = update.effective_chat.id
    query = update.callback_query
    contractor = context.user_data['user'].contractor
    is_call_handlers = False

    message = 'Я вас не понял, нажмите одну из предложенных кнопок'  # answer when no one of if is True
    if query and query.data in ['get_back', 'return_to_start']:
        return start_contractor(update, context)
    elif query and query.data == 'how_contractor_bot_work':  # contractor request a help
        message = dedent('''
        При появлении новых заказов вам будет приходить уведомление,
        где вы можете взять заказ в работу

        Также текущие доступные заказы вы можете посмотреть по кнопке "Посмотреть заказы"

        Когда вы возьмете заказ вам придет логин и пароль от админки клиента

        Если у вас возникнут вопросы, вы всегда можете задать их заказчику по кнопке "Написать заказчику"

        Как только заказчик вам ответит вам придет уведомление

        После завершения заказа нажмите на кнопку "Завершить заказ"

        Посмотреть сколько заказов вы выполнили и заработает при очередном финансовом
        периоде вы можете по кнопке "Мой заработок за месяц"
        ''')
    elif query and query.data == 'watch_orders':  # contractor request to watch list of available orders
        is_return, what_return, message = handle_watch_orders_callback(update, context, chat_id)
        is_call_handlers = True
    elif query and query.data == 'send_message_to_client':  # contractor request to send message to client
        is_return, what_return, message = handle_send_message_to_client_callback(context, contractor, chat_id)
        is_call_handlers = True
    elif query and query.data == 'close_order':  # contractor request to close active order
        is_return, what_return, message = handle_close_order_callback(context, contractor)
        is_call_handlers = True
    elif query and query.data == 'my_salary':  # contractor request to get his salary in this month
        is_return, what_return, message = handle_my_salary_callback(contractor)
        is_call_handlers = True
    elif query and query.data.startswith('take_order'):  # contractor request to take order
        is_return, what_return, message = handle_take_order_callback(update, context, contractor, chat_id)
        is_call_handlers = True

    if is_call_handlers and is_return:
        return what_return

    context.bot.send_message(text=message, chat_id=chat_id)

    return start_contractor(update, context)


def wait_message_to_client_contractor(update: Update, context: CallbackContext) -> str:
    """Handler of waiting contractor message to client"""
    chat_id = update.effective_chat.id
    query = update.callback_query
    no_text_message = True
    if update.message:
        message_to_client = update.message.text
        no_text_message = False
    contractor = context.user_data['user'].contractor

    if query and query.data in ['get_back', 'return_to_start']:
        return start_contractor(update, context)
    elif not contractor.has_order_in_work() or no_text_message:  # if order disappeared or contractor send not a text
        message = 'Что-то пошло не так, попробуйте снова'
    else:
        order = contractor.get_order_in_work()

        # send message to client
        client_chat_id = order.client.telegram_id
        message_to_client = f'Вам сообщение от подрядчика вашего заказа:\n\n{message_to_client}'
        context.bot.send_message(text=message_to_client, chat_id=client_chat_id)

        message = 'Сообщение успешно отправлено, когда заказчик ответит вам придет уведомление'
    context.bot.send_message(text=message, chat_id=chat_id)

    return start_contractor(update, context)


def wait_estimate_contractor(update: Update, context: CallbackContext) -> str:
    """Handler of waiting estimate from contractor while he is giving an order"""
    chat_id = update.effective_chat.id
    query = update.callback_query
    no_text_message = True
    if update.message:
        estimated_time_hours = update.message.text
        no_text_message = False
    order_in_process = context.user_data['order_in_process']
    contractor = context.user_data['user'].contractor
    if query and query.data == 'return_to_start':
        return start_contractor(update, context)
    elif order_in_process and order_in_process.status != Order.Status.created:  # check if order available and in context
        message = 'К сожалению заказ уже взяли, попробуйте снова получить список заказов'
    elif no_text_message or not order_in_process:  # check if contractor send text message
        message = 'Что-то пошло не так, попробуйте снова'
        context.bot.send_message(text=message, chat_id=chat_id)
        return 'WAIT_ESTIMATE_CONTRACTOR'
    else:
        try:
            estimated_time_hours = int(estimated_time_hours)
            if 1 <= estimated_time_hours <= 24:  # limit from DB
                client_chat_id = order_in_process.client.telegram_id
                order_in_process.take_in_work(contractor, estimated_time_hours)
                context.user_data['order_in_process'] = None
                message_to_client = 'Ваш заказ взят работу! При выполнении пришлем уведомление.'
                context.bot.send_message(text=message_to_client, chat_id=client_chat_id)
                # TODO: дешифрование кредсов
                message = dedent(f'''
                Заказ успешно взят в работу, приятной работы

                Доступы к сайту:
                {order_in_process.creds}
                ''')
            else:
                message = 'Оценка должна быть от 1 до 24 часов, попробуйте снова или обратитесь к менеджеру'
                keyboard = [
                    [InlineKeyboardButton('Вернуться в начало', callback_data='return_to_start')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_message(text=message, chat_id=chat_id, reply_markup=reply_markup)
                return 'WAIT_ESTIMATE_CONTRACTOR'
        except ValueError:
            # estimate not a number
            message = 'Не удалось преобразовать вашу оценку в целое число, попробуйте снова'
            context.bot.send_message(text=message, chat_id=chat_id)
            return 'WAIT_ESTIMATE_CONTRACTOR'

    context.bot.send_message(text=message, chat_id=chat_id)
    return start_contractor(update, context)
