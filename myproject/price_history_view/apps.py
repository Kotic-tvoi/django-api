# price_history_view/apps.py
import logging

from django.apps import AppConfig
from django.conf import settings


logger = logging.getLogger(__name__)


class PriceHistoryViewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "price_history_view"
    verbose_name = "Price History"

    def ready(self):
        """Запускает сбор истории цен только при включённом feature-флаге."""
        if not getattr(settings, "PRICE_HISTORY_VIEW_ENABLED", False):
            logger.info("Price history is disabled; APScheduler was not started")
            return

        if not getattr(settings, "APSCHEDULER_AUTOSTART", False):
            logger.info("APScheduler autostart is disabled")
            return

        try:
            from . import jobs
            jobs.start()
        except Exception as exc:
            logger.exception("Failed to start APScheduler: %s", exc)
