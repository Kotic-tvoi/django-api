# price_history_view/jobs.py
import logging
import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from django.core.management import call_command

logger = logging.getLogger(__name__)
_scheduler = None


def run_fetch_prices():
    logger.info("Running job: fetch_prices")
    call_command("fetch_prices")


def run_purge_old_prices():
    logger.info("Running job: purge_old_prices")
    call_command("purge_old_prices", days=30)


def start():
    """
    Универсальный запуск APScheduler:
    - Не пишет в SQLite (MemoryJobStore)
    - Работает в runserver без ошибок
    - Подойдёт и для будущего продакшена, если вынести в systemd
    """
    global _scheduler
    if _scheduler:
        return

    scheduler = BackgroundScheduler(
        timezone=pytz.timezone("Europe/Moscow")
    )

    # ❗ НЕ используем DjangoJobStore → SQLite не блокируется
    scheduler.add_jobstore(MemoryJobStore())

    # сбор цен каждые 15 минут
    scheduler.add_job(
        run_fetch_prices,
        trigger="interval",
        minutes=15,
        id="fetch_prices_job",
        replace_existing=True,
    )

    # очистка старых цен — раз в сутки
    scheduler.add_job(
        run_purge_old_prices,
        trigger="cron",
        hour=3,
        minute=15,
        id="purge_old_prices_job",
        replace_existing=True,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler started")

    return scheduler
