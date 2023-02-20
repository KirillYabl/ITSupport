from telegram import Update
from telegram.ext import CallbackContext


def start_not_found(update: Update, context: CallbackContext) -> str:
    """Unknown start function which send a menu"""
    chat_id = update.effective_chat.id
    message = 'Вы не являетесь нашим клиентом, пожалуйста обратитесь к менеджеру'
    context.bot.send_message(text=message, chat_id=chat_id)
    return 'START'
