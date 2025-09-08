# API_ShowPrice/management/commands/fetch_prices.py

from django.core.management.base import BaseCommand
from django.utils import timezone

from API_ShowPrice.models import PriceRecord
from API_ShowPrice.parser import ParseWB, partners  # dict {id: name}
from API_ShowPrice.pydantic_models import Items


def _rub_int(value) -> int:
    """Из копеек → ЦЕЛЫЕ рубли (округление к ближайшему)."""
    try:
        v = int(value)
    except Exception:
        return 0
    return (v + 50) // 100


class Command(BaseCommand):
    help = "Fetch current prices and store snapshots in DB (integer RUB, dest disabled)"

    def add_arguments(self, parser):
        parser.add_argument("--partner-id", type=int, help="Fetch only this partner_id")

    def handle(self, *args, **options):
        now = timezone.now()

        # либо один партнёр из опции, либо все из словаря partners
        partner_ids = [options["partner_id"]] if options.get("partner_id") else list(partners.keys())

        total_rows = 0

        for pid in partner_ids:
            # ВАЖНО: ParseWB ждёт URL вида .../seller/{id}?brand=279103
            url = f"https://www.wildberries.ru/seller/{pid}?brand=279103"
            try:
                parser = ParseWB(url=url)  # dest оставим по умолчанию ('-1257786')
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Parser init failed for partner {pid}: {e}"))
                continue

            try:
                # get_items() без аргументов (сигнатура: def get_items(self))
                items: Items = parser.get_items()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to fetch items for partner {pid}: {e}"))
                continue

            batch = []
            for product in getattr(items, "products", []):
                try:
                    size0 = product.sizes[0]
                    basic = _rub_int(getattr(size0.price, "basic", 0))
                    product_price = _rub_int(getattr(size0.price, "product", 0))
                    item_id = int(product.id)
                    name = (product.name or "")[:255]
                except Exception:
                    # пропускаем «битые» позиции
                    continue

                batch.append(PriceRecord(
                    created_at=now,        # единая метка времени — один «снимок»
                    partner_id=pid,
                    dest="",               # регионы отключены в хранилище
                    item_id=item_id,
                    item_name=name,
                    price_basic=basic,     # ЦЕЛЫЕ рубли
                    price_product=product_price,
                ))

            if batch:
                PriceRecord.objects.bulk_create(batch, ignore_conflicts=True)
                total_rows += len(batch)

        self.stdout.write(self.style.SUCCESS(
            f"Saved ~{total_rows} rows at {now:%Y-%m-%d %H:%M:%S} (partners={len(partner_ids)})"
        ))
