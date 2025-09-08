import logging
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django_apscheduler.models import DjangoJobExecution

# Импорт management-команды как callable (используется в run_fetch_prices)
from API_ShowPrice.management.commands.fetch_prices import Command as FetchPricesCommand

logger = logging.getLogger(__name__)
_scheduler = None


def delete_old_job_executions(max_age: int = 7 * 24 * 60 * 60) -> None:
    """Чистим записи о выполнениях задач старше max_age секунд (по умолчанию 7 дней)."""
    threshold = timezone.now() - timedelta(seconds=max_age)
    DjangoJobExecution.objects.filter(run_time__lt=threshold).delete()


# === Функции заданий — на верхнем уровне (сериализуемые) ===

def run_fetch_prices() -> None:
    """Запускает сбор цен (эквивалент `python manage.py fetch_prices`)."""
    logger.info("Running job: fetch_prices")
    FetchPricesCommand().handle()


def run_cleanup_job_executions() -> None:
    """Ежедневная очистка истории выполнений планировщика."""
    logger.info("Running job: cleanup job executions")
    delete_old_job_executions()


def start() -> None:
    """
    Запуск APScheduler один раз. В dev-режиме Django перезапускает код —
    поэтому не даём стартовать планировщику дважды.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        logger.info("APScheduler: already running, skip start()")
        return

    # В dev-сервере Django есть первичный процесс автоперезагрузчика — в нём не стартуем
    if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
        return

    scheduler = BackgroundScheduler(
        timezone=settings.TIME_ZONE if getattr(settings, "USE_TZ", False) else None
    )
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # ВАЖНО: используем строковые ссылки в формате module:function (через двоеточие)
    scheduler.add_job(
        id="fetch_prices_every_5m",
        func="API_ShowPrice.jobs:run_fetch_prices",          # ← двоеточие
        trigger="interval",
        minutes=15,
        jobstore="default",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        id="cleanup_old_job_executions_daily",
        func="API_ShowPrice.jobs:run_cleanup_job_executions",  # ← двоеточие
        trigger="cron",
        hour=3,
        minute=0,
        jobstore="default",
        replace_existing=True,
        max_instances=1,
    )

    register_events(scheduler)
    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler started")
