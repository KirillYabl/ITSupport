from django.conf import settings
from django.core.management import BaseCommand

from tgbot_app.tg_bot import TgBot

from tgbot_app.client_state_functions import start_client
from tgbot_app.client_state_functions import handle_menu_client
from tgbot_app.client_state_functions import wait_message_to_contractor_client
from tgbot_app.client_state_functions import waiting_order_task
from tgbot_app.client_state_functions import waiting_credentials

from tgbot_app.manager_state_functions import start_manager
from tgbot_app.manager_state_functions import handle_menu_manager

from tgbot_app.contractor_state_functions import start_contractor
from tgbot_app.contractor_state_functions import handle_menu_contractor
from tgbot_app.contractor_state_functions import wait_message_to_client_contractor
from tgbot_app.contractor_state_functions import wait_estimate_contractor

from tgbot_app.owner_state_functions import start_owner
from tgbot_app.owner_state_functions import handle_menu_owner
from tgbot_app.owner_state_functions import waiting_username_client_add
from tgbot_app.owner_state_functions import waiting_username_contractor_add
from tgbot_app.owner_state_functions import waiting_username_manager_add
from tgbot_app.owner_state_functions import waiting_username_owner_add
from tgbot_app.owner_state_functions import waiting_username_client_delete
from tgbot_app.owner_state_functions import waiting_username_contractor_delete
from tgbot_app.owner_state_functions import waiting_username_manager_delete
from tgbot_app.owner_state_functions import waiting_username_owner_delete

from tgbot_app.unknown_state_functions import start_not_found


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_bot()
        except Exception as exc:
            raise exc


def start_bot():
    bot = TgBot(
        settings.TELEGRAM_ACCESS_TOKEN,
        {
            'Клиент': {
                'START': start_client,
                'HANDLE_MENU_CLIENT': handle_menu_client,
                'WAIT_MESSAGE_TO_CONTRACTOR_CLIENT': wait_message_to_contractor_client,
                'WAITING_ORDER_TASK': waiting_order_task,
                'WAITING_CREDENTIALS': waiting_credentials,
            },
            'Менеджер': {
                'START': start_manager,
                'HANDLE_MENU_MANAGER': handle_menu_manager
            },
            'Подрядчик': {
                'START': start_contractor,
                'HANDLE_MENU_CONTRACTOR': handle_menu_contractor,
                'WAIT_MESSAGE_TO_CLIENT_CONTRACTOR': wait_message_to_client_contractor,
                'WAIT_ESTIMATE_CONTRACTOR': wait_estimate_contractor,
            },
            'Владелец': {
                'START': start_owner,
                'HANDLE_MENU_OWNER': handle_menu_owner,
                'WAITING_USERNAME_CLIENT_ADD': waiting_username_client_add,
                'WAITING_USERNAME_CONTRACTOR_ADD': waiting_username_contractor_add,
                'WAITING_USERNAME_MANAGER_ADD': waiting_username_manager_add,
                'WAITING_USERNAME_OWNER_ADD': waiting_username_owner_add,
                'WAITING_USERNAME_CLIENT_DELETE': waiting_username_client_delete,
                'WAITING_USERNAME_CONTRACTOR_DELETE': waiting_username_contractor_delete,
                'WAITING_USERNAME_MANAGER_DELETE': waiting_username_manager_delete,
                'WAITING_USERNAME_OWNER_DELETE': waiting_username_owner_delete,
            },
            'unknown': {
                'START': start_not_found,
            },
        }
    )
    bot.updater.start_polling()
    bot.updater.idle()
