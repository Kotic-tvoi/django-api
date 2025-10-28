# price_history_view/apps.py
from django.apps import AppConfig
from django.conf import settings
import logging

class PriceHistoryViewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "price_history_view"
    verbose_name = "Price History"

    def ready(self):
        if getattr(settings, "APSCHEDULER_AUTOSTART", True):
            try:
                from . import jobs   # <- импорт тут, а не сверху файла
                jobs.start()
            except Exception as e:
                logging.getLogger(__name__).exception("Failed to start APScheduler: %s", e)
