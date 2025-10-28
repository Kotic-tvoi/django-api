from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from price_history_view.models import PriceRecord


class Command(BaseCommand):
    help = "Удаляет записи PriceRecord старше N дней (по умолчанию 30)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Сколько дней хранить (default: 30)")

    def handle(self, *args, **opts):
        days = int(opts["days"])
        cutoff = timezone.now() - timedelta(days=days)
        qs = PriceRecord.objects.filter(created_at__lt=cutoff)

        # Простой и быстрый путь (PostgreSQL/SQLite нормально переживут bulk delete)
        deleted, _ = qs.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Purged {deleted} PriceRecord rows older than {days} days (before {cutoff.isoformat()})"
        ))
