from django.conf import settings
from django.core.management import BaseCommand

from user_app.tg_bot import TgBot, echo


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start_bot()
        except Exception as exc:
            raise exc


def start_bot():

    bot = TgBot(
        settings.TELEGRAM_ACCESS_TOKEN,
        {'echo': echo}
    )
    bot.updater.start_polling()
    bot.updater.idle()
