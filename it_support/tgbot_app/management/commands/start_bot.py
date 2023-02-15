from django.conf import settings
from django.core.management import BaseCommand

from tgbot_app.tg_bot import TgBot
from tgbot_app.tg_bot import start_client
from tgbot_app.tg_bot import start_manager
from tgbot_app.tg_bot import start_contractor
from tgbot_app.tg_bot import start_not_found
from tgbot_app.tg_bot import handle_contacts


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
                'HANDLE_CONTACTS': handle_contacts
            },
            'Подрядчик': {
                'START': start_contractor,
            },
            'unknown': {
                'START': start_not_found,
            },
        }
    )
    bot.updater.start_polling()
    bot.updater.idle()
