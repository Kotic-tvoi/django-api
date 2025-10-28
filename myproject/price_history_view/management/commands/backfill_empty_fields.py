# price_history_view/management/commands/backfill_empty_fields.py
from django.core.management.base import BaseCommand
from django.db.models import F
from price_history_view.models import PriceRecord
from get_price.parser import partners

class Command(BaseCommand):
    help = "Fill missing partner_name, article, price_before_spp for old rows"

    def handle(self, *args, **opts):
        # 1) до СПП = basic, где пусто
        n1 = PriceRecord.objects.filter(price_before_spp__isnull=True).update(
            price_before_spp=F("price_basic")
        )
        # 2) partner_name из словаря, где пусто
        n2 = 0
        for pid, pname in partners.items():
            n2 += PriceRecord.objects.filter(partner_id=pid, partner_name="").update(partner_name=pname)
        # 3) article — если хочешь, оставим пустым (нет источника), иначе допиши логику
        self.stdout.write(self.style.SUCCESS(f"filled: before_spp={n1}, partner_name={n2}"))
