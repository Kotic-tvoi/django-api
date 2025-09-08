from django.apps import AppConfig
from django.conf import settings


class ApiShowpriceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'API_ShowPrice'
    verbose_name = "API — ShowPrice"

    def ready(self):
        # Автозапуск планировщика можно контролировать флагом в settings
        if getattr(settings, "APSCHEDULER_AUTOSTART", True):
            # Импорт тут, чтобы не вызывать его на этапе загрузки модулей до конфигов
            from API_ShowPrice import jobs
            try:
                jobs.start()
            except Exception as e:
                # Не заваливаем проект, просто логируем
                import logging
                logging.getLogger(__name__).exception("Failed to start APScheduler: %s", e)
