from django.conf import settings
from django.core.management import BaseCommand

from tgbot_app.tg_bot import TgBot

from tgbot_app.tg_bot import start_client

from tgbot_app.tg_bot import start_manager
from tgbot_app.tg_bot import handle_menu_manager

from tgbot_app.tg_bot import start_contractor
from tgbot_app.tg_bot import handle_menu_contractor

from tgbot_app.tg_bot import start_owner
from tgbot_app.tg_bot import handle_menu_owner

from tgbot_app.tg_bot import start_not_found


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
            },
            'Менеджер': {
                'START': start_manager,
                'HANDLE_MENU_MANAGER': handle_menu_manager
            },
            'Подрядчик': {
                'START': start_contractor,
                'HANDLE_MENU_CONTRACTOR': handle_menu_contractor,
            },
            'Владелец': {
                'START': start_owner,
                'HANDLE_MENU_OWNER': handle_menu_owner
            },
            'unknown': {
                'START': start_not_found,
            },
        }
    )
    bot.updater.start_polling()
    bot.updater.idle()
