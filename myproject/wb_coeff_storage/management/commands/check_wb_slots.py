from django.core.management.base import BaseCommand
from wb_coeff_storage.services import check_wb_slots_and_prepare_message
from wb_coeff_storage.telegram import send_telegram_message

class Command(BaseCommand):
    help = "Проверить свободные слоты WB и отправить уведомление в Telegram (если есть свежие)."

    def handle(self, *args, **options):
        msg = check_wb_slots_and_prepare_message()
        if msg:
            send_telegram_message(msg)
            self.stdout.write(self.style.SUCCESS("Уведомление отправлено."))
        else:
            self.stdout.write("Свежих интересных слотов нет.")
