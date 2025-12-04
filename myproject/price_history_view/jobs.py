"""Планировщик запуска программ"""
import logging
import os
import pytz
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django_apscheduler.models import DjangoJobExecution

# Импорт management-команды как callable (используется в run_fetch_prices)
from price_history_view.management.commands.fetch_prices import Command as FetchPricesCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)
_scheduler = None


def delete_old_job_executions(max_age: int = 7 * 24 * 60 * 60) -> None:
    """Чистим записи о выполнениях задач старше max_age секунд (по умолчанию 7 дней)."""
    threshold = timezone.now() - timedelta(seconds=max_age)
    DjangoJobExecution.objects.filter(run_time__lt=threshold).delete()


# === Функции заданий — на верхнем уровне (сериализуемые) ===
def run_purge_old_prices() -> None:
    """Удаление записей больше days дней"""
    logger.info("Running job: purge_old_prices")
    call_command("purge_old_prices", days=30)


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
    if _scheduler:
        return

    scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Запуск сбора цен каждые n минут
    scheduler.add_job(
        run_fetch_prices,
        trigger="interval",
        minutes=15,      # для теста ставим 1 минуту
        id="fetch_prices_job",
        replace_existing=True
    )

    # Очистка логов ежедневно
    scheduler.add_job(
        run_cleanup_job_executions,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup_job_executions",
        replace_existing=True,
    )

    # Удаление записей старше 30 дней
    scheduler.add_job(
        run_purge_old_prices,
        trigger="cron",
        hour=3,
        minute=15,
        id="purge_old_prices",
        replace_existing=True,
    )

    register_events(scheduler)
    scheduler.start()

    _scheduler = scheduler
    logger.info("APScheduler started")