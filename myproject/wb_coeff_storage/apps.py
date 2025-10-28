from django.apps import AppConfig
import logging
from django.conf import settings

class WbCoeffStorageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wb_coeff_storage'

    def ready(self):
        if getattr(settings, "APSCHEDULER_AUTOSTART", True):
            try:
                from . import jobs
                jobs.start()
            except Exception as e:
                logging.getLogger(__name__).exception("Failed to start APScheduler for wb_coeff_storage: %s", e)
