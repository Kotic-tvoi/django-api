# price_history_view/management/commands/fetch_prices.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from price_history_view.models import PriceRecord
from get_price.parser import ParseWB, partners, dest_name  # partners — твой словарь

def fetch_partner_items(partner_id: int, dest: str):
    items = ParseWB(f"https://www.wildberries.ru/seller/{partner_id}", dest=dest).get_items()
    rows = []
    for p in items.products:
        try:
            basic = int(p.sizes[0].price.basic / 100)
            product = int(p.sizes[0].price.product / 100)
        except Exception:
            continue
        # бук. артикул — подстрой под твои pydantic-модели
        vendor = getattr(p, "vendorCode", "") or getattr(p, "supplierVendorCode", "") or ""
        rows.append({
            "item_id": p.id,
            "item_name": p.name,
            "price_basic": basic,
            "price_product": product,
            "article": vendor,
        })
    return rows

class Command(BaseCommand):
    help = "Fetch WB prices and save snapshots"

    def handle(self, *args, **opts):
        now = timezone.now()
        dest = str(dest_name["Москва"])  # если у тебя используется регион

        bulk = []
        for partner_id, partner_name in partners.items():
            for r in fetch_partner_items(partner_id, dest):
                bulk.append(PriceRecord(
                    created_at=now,
                    partner_id=partner_id,
                    partner_name=partner_name,           # ← ЗАПОЛНЯЕМ
                    dest=dest,
                    item_id=r["item_id"],
                    item_name=r["item_name"],
                    article=r["article"],               # ← ЗАПОЛНЯЕМ
                    price_basic=r["price_basic"],
                    price_before_spp=r["price_basic"],  # ← ПОКА ТАК (до СПП = basic)
                    price_product=r["price_product"],
                ))
        PriceRecord.objects.bulk_create(bulk, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"Saved {len(bulk)} rows"))
