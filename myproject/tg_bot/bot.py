from telegram.ext import Updater, CommandHandler
import os
from dotenv import load_dotenv
from services import get_filtered_warehouses
from telegram import ParseMode

ALLOWED_USERS = [1145370467]

# Получаем токен из .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def restricted(func):
    def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USERS:
            update.message.reply_text("⛔ У вас нет доступа к этому боту.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper


@restricted
def start(update, context):
    update.message.reply_text("👋 Привет! Я бот для бронирования поставок на WB.\n\nНапиши /get_warehouses чтобы получить список складов.")


@restricted
def create_booking(update, context):
    try:
        warehouses, warehouse_map = get_filtered_warehouses()
        if not warehouses:
            update.message.reply_text("❌ Не удалось получить список складов.")
            return

        # Формируем сообщение
        message = "📦 *Склады, принимающие «Короба»*:\n\n"
        for warehouse in warehouses:
            message += f"• {warehouse}\n"

        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        update.message.reply_text(f"❌ Ошибка при обработке запроса: {e}")


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get_warehouses", create_booking))

    print("🤖 Бот запущен.")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
