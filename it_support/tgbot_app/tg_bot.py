from textwrap import dedent
from typing import Callable

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update

from support_app.models import BotUser
from support_app.models import Contractor
from support_app.models import Client
from support_app.models import Manager
from support_app.models import Order


def get_user(func: Callable) -> Callable:
    """Decorator to add user in context when telegram handlers starts"""

    def wrapper(update: Update, context: CallbackContext) -> str:
        chat_id = update.effective_chat.id
        username = update.effective_user.username

        try:
            active_users = BotUser.objects.active()
            try:
                user = active_users.get(telegram_id=chat_id)
                if user.tg_nick != username:
                    user.tg_nick = username
                    user.save()
            except BotUser.DoesNotExist:
                user = active_users.get(tg_nick=username)
                if user.telegram_id != chat_id:
                    user.telegram_id = chat_id
                    user.save()
        except BotUser.DoesNotExist:
            user = None

        context.user_data['user'] = user
        return func(update, context)

    return wrapper


class TgBot(object):

    def __init__(self, tg_token: str, states_functions: dict[str, dict[str, Callable]]) -> None:
        """
            states_functions not dict[str, Callable] because it contains many bots like:
            states_functions = {
                'bot_1': {
                    'state_1_bot_1': func1_bot1,
                    'state_2_bot_1': func2_bot1,
                },
                'bot_2': {
                    'state_1_bot_2': func1_bot2,
                    'state_2_bot_2': func2_bot2,
                }
            }
        """
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

    def handle_users_reply(self, update: Update, context: CallbackContext) -> None:
        """
        State machine of bot.

        Current state of user record to DB
        """
        user = context.user_data['user']

        if user is None:
            self.states_functions['unknown']['START'](update, context)
            return

        if update.message:
            user_reply = update.message.text
        elif update.callback_query:
            user_reply = update.callback_query.data
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

    def error(self, update: Update, context: CallbackContext) -> None:
        """Error handler"""
        print(f'Update "{update}" caused error "{context.error}"')
        raise context.error

    def help_handler(self, update: Update, context: CallbackContext) -> None:
        """help handler"""
        update.message.reply_text("Используйте /start для того, что бы перезапустить бот")

    def handle_warning_orders_not_in_work(self, context: CallbackContext) -> None:
        """If there are an overdue orders they should be sended to every manager"""
        warning_orders_not_in_work = Order.objects.get_warning_orders_not_in_work()
        if not warning_orders_not_in_work:  # если не будет просроченных заказов, то не отправляем
            return
        message = 'Есть заказы, которые долго не берут в работу\n\n' + '\n'.join(
            [
                f'Задача: {order.task} \nКонтакт клиента: @{order.client.tg_nick}\n\n'
                for order in warning_orders_not_in_work
            ]
        )
        managers = Manager.objects.active()
        for manager in managers:
            context.bot.send_message(text=message, chat_id=manager.telegram_id)
        warning_orders_not_in_work.update(not_in_work_manager_informed=True)

    def handle_warning_orders_not_closed(self, context: CallbackContext) -> None:
        """
        Каждому менеджеру отправить сообщение по каждому не выполненному заказу
        В сообщении указать задачу (поле task у заказа) и
        контакты заказчика (поле client.tg_nick у заказа) и
        подрядчика (поле contractor.tg_nick у заказа) не забыв добавить @
        """
        warning_orders_not_closed = Order.objects.get_warning_orders_not_closed()
        # managers = Manager.objects.active()

        # warning_orders_not_closed.update(late_work_manager_informed=True)  # это в конце вызывается


def start_not_found(update: Update, context: CallbackContext) -> str:
    """Ответ для неизвестного, что мы его не знаем ему нужно связаться с админами"""
    return 'START'


# Функции для менеджера
def start_manager(update: Update, context: CallbackContext) -> str:
    """Manager start function which send a menu"""
    keyboard = [
        [InlineKeyboardButton('Контакты доступных подрядчиков', callback_data='contacts_available_contractors')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id
    context.bot.send_message(text='Что вас интересует', reply_markup=reply_markup, chat_id=chat_id)
    return 'HANDLE_MENU_MANAGER'


def handle_menu_manager(update: Update, context: CallbackContext) -> str:
    """Manager menu handler, also answer if unknown enter"""
    chat_id = update.effective_chat.id
    query = update.callback_query

    message = 'Я вас не понял, выберите из предложенных кнопок'
    if query and query.data == 'contacts_available_contractors':
        available_contractors = Contractor.objects.get_available()
        message = '\n'.join([f'@{contractor.tg_nick}' for contractor in available_contractors])

    context.bot.send_message(text=message, chat_id=chat_id)
    return start_manager(update, context)


# Функции для клиента
def start_client(update: Update, context: CallbackContext) -> str:
    """Ответ для клиента"""
    return ''  # TODO: придумать название


# Функции для подрядчика
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


def handle_menu_contractor(update: Update, context: CallbackContext) -> str:
    """Manager menu handler"""
    chat_id = update.effective_chat.id
    query = update.callback_query
    contractor = context.user_data['user'].contractor

    message = 'Я вас не понял, нажмите одну из предложенных кнопок'  # answer when no one of if is True
    if query and query.data == 'how_contractor_bot_work':  # contractor request a help
        message = dedent(f'''
        При появлении новых заказов вам будет приходить уведомление, 
        где вы можете взять заказ в работу
                             
        Также текущие доступные заказы вы можете посотреть по кнопке "Посмотреть заказы"
                             
        Когда вы возьмете заказ вам придет логин и пароль от админки клиента
                             
        Если у вас возникнут вопросы, вы всегда можете задать их заказчику по кнопке "Написать заказчику"
        
        Как только заказчик вам ответит вам придет уведомление
        
        После завершения заказа нажмите на кнопку "Завершить заказ"
        
        Посмотреть сколько заказов вы выполнили и заработает при очередном финансовом 
        периоде вы можете по кнопке "Мой заработок за месяц" 
        ''')
    elif query and query.data == 'watch_orders':  # contractor request to watch list of available orders
        available_orders = Order.objects.get_available()
        if not available_orders:
            message = 'Нет заказов, которые можно взять в работу'
        for order in available_orders:
            # send every order in different message because it contains button to take order
            message = dedent(f'''Задание:
            {order.task}
            
            Доступы к сайту:
            {order.creds}
            ''')
            keyboard = [[InlineKeyboardButton('Взять в работу', callback_data=f'take_order|{order.pk}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(text=message, reply_markup=reply_markup, chat_id=chat_id)
            return 'HANDLE_MENU_CONTRACTOR'
    elif query and query.data == 'send_message_to_client':  # contractor request to send message to client
        message = 'У вас нет активного заказа'
        if contractor.has_order_in_work():
            message = 'Напишите сообщение клиенту'
            context.bot.send_message(text=message, chat_id=chat_id)
            return 'WAIT_MESSAGE_TO_CLIENT_CONTRACTOR'
    elif query and query.data == 'close_order':  # contractor request to close active order
        message = 'У вас нет активного заказа'
        if contractor.has_order_in_work():
            contractor.get_order_in_work().close_work()
            message = 'Спасибо за вашу работу! Теперь вы можете брать новый заказ'
    elif query and query.data == 'my_salary':  # contractor request to get his salary in this month
        closed_orders_count = contractor.get_closed_in_actual_billing_orders().count()
        order_rate = 500  # TODO get normal order rate from DB
        salary = closed_orders_count * order_rate
        message = f'Выполнено заказав в отчетном периоде: {closed_orders_count}. К выплате {salary}'
    elif query and query.data.startswith('take_order'):  # contractor request to take order
        order_pk = query.data.split('|')[-1]
        bad_scenario = False

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
            message = dedent('''Пришлите приблизительную оценку требуемого на выполнения времени в часах
                                Оценка от 1 до 24 часов, если вы считаете, что заказ потребует больше времени
                                обратитесь к менеджерам, мы не оказываем проектную поддержку''')
            context.user_data['order_in_process'] = order
            context.bot.send_message(text=message, chat_id=chat_id)
            return 'WAIT_ESTIMATE_CONTRACTOR'

    context.bot.send_message(text=message, chat_id=chat_id)

    return start_contractor(update, context)


def wait_message_to_client_contractor(update: Update, context: CallbackContext) -> str:
    """Handler of waiting contractor message to client"""
    chat_id = update.effective_chat.id
    no_text_message = True
    if update.message:
        message_to_client = update.message.text
        no_text_message = False
    contractor = context.user_data['user'].contractor

    if not contractor.has_order_in_work() or no_text_message:  # if order disappeared or contractor send not a text
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
    no_text_message = True
    if update.message:
        estimated_time_hours = update.message.text
        no_text_message = False
    order_in_process = context.user_data['order_in_process']
    contractor = context.user_data['user'].contractor

    if order_in_process and order_in_process.status != Order.Status.created:  # check if order available and in context
        message = 'К сожалению заказ уже взяли, попробуйте снова получить список заказов'
    elif no_text_message or not order_in_process:  # check if contractor send text message
        message = 'Что-то пошло не так, попробуйте снова'
        context.bot.send_message(text=message, chat_id=chat_id)
        return 'WAIT_ESTIMATE_CONTRACTOR'
    else:
        try:
            estimated_time_hours = int(estimated_time_hours)
            if 1 <= estimated_time_hours <= 24:  # limit from DB
                order_in_process.take_in_work(contractor, estimated_time_hours)
                message = 'Заказ успешно взят в работу, приятной работы'
            else:
                message = 'Оценка должна быть от 1 до 24 часов, попробуйте снова или обратитесь к менеджеру'
                context.bot.send_message(text=message, chat_id=chat_id)
                return 'WAIT_ESTIMATE_CONTRACTOR'
        except ValueError:
            # estimate not a number
            message = 'Не удалось преобразовать вашу оценку в целое число, попробуйте снова'
            context.bot.send_message(text=message, chat_id=chat_id)
            return 'WAIT_ESTIMATE_CONTRACTOR'

    context.bot.send_message(text=message, chat_id=chat_id)
    return start_contractor(update, context)


# Функции для владельца
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
        billing = [
            f'{contractor_billing["contractor__tg_nick"]}\t{contractor_billing["count_orders"]}'
            for contractor_billing
            in Order.objects.calculate_billing()
        ]
        message = 'Подрядчик\tВыполненных заказов\n' + '-' * 50 + '\n' + '\n'.join(billing)
    elif query and query.data.startswith('orders_stats'):  # owner request a stats of clients
        stats = [
            f'{stat[0]}\t{stat[1]}\t{stat[2]}'
            for stat
            in Order.objects.calculate_average_orders_in_month()
        ]
        message = 'Начало биллинга\tКлиент\tЧисло заказов\n' + '-' * 50 + '\n' + '\n'.join(stats)

    context.bot.send_message(text=message, chat_id=chat_id)
    return start_owner(update, context)
