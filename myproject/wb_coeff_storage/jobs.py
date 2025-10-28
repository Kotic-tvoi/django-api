import logging
import os
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from django.core.management import call_command

logger = logging.getLogger(__name__)
_scheduler = None

def run_check_wb_slots():
    """Вызываем management-команду — так удобнее поддерживать единый вход."""
    call_command("check_wb_slots")

def start():
    global _scheduler
    if _scheduler is not None:
        return

    # В дев-режиме не дублируем запуск из-за авто-перезапуска runserver
    if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
        return

    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        id="wb_slots_every_2m",
        func="wb_coeff_storage.jobs:run_check_wb_slots",
        trigger="interval",
        minutes=2,
        jobstore="default",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )

    register_events(scheduler)
    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler (wb_coeff_storage) started")
