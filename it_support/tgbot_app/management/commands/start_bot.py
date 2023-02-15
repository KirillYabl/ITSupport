from django.conf import settings
from django.core.management import BaseCommand

from tgbot_app.tg_bot import TgBot
from tgbot_app.tg_bot import start_client
from tgbot_app.tg_bot import start_manager
from tgbot_app.tg_bot import start_contractor
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
            'client': {
                'start': start_client
            },
            'manager': {
                'start': start_manager
            },
            'contractor': {
                'start': start_contractor
            },
            'unknown': {
                'start': start_not_found
            },
        }
    )
    bot.updater.start_polling()
    bot.updater.idle()
