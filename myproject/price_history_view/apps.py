# price_history_view/apps.py
from django.apps import AppConfig
import logging

class PriceHistoryViewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "price_history_view"
    verbose_name = "Price History"

    def ready(self):
        """
        Минимальный запуск APScheduler ТОЛЬКО для runserver.
        Без проверок DEBUG, RUN_MAIN, systemd, gunicorn.
        """
        try:
            from . import jobs
            jobs.start()
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to start APScheduler: %s", e)
