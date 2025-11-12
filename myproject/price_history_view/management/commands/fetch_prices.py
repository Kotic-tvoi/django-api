import logging
import os
import time
from typing import Optional

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from price_history_view.models import PriceRecord
from get_price.parser import ParseWB, partners

log = logging.getLogger(__name__)

WB_URL = "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter"
JK_PARTNER_ID = 215484  # JKeratin


def build_parser(partner_id: int) -> ParseWB:
    """
    Конструктор парсера: пробуем передать seller_id,
    если либе нужен URL — собираем URL.
    """
    try:
        return ParseWB(seller_id=partner_id)  # если поддерживается
    except TypeError:
        url = f"https://www.wildberries.ru/seller/{partner_id}"
        return ParseWB(url)


def fetch_partner_items(partner_id: int) -> list[dict]:
    """
    Возвращает список словарей с данными по товарам партнёра:
    item_id, item_name, article, price_basic, price_product.
    """
    parser = build_parser(partner_id)
    items = parser.get_items()
    rows: list[dict] = []

    for p in getattr(items, "products", []):
        try:
            basic = int(p.sizes[0].price.basic / 100)
            product = int(p.sizes[0].price.product / 100)
        except Exception:
            # если нет цен — пропускаем товар
            continue

        # буквеный артикул (где есть)
        article = (
            getattr(p, "vendorCode", None)
            or getattr(p, "supplierVendorCode", None)
            or ""
        )

        rows.append(
            {
                "item_id": int(p.id),
                "item_name": p.name,
                "article": article,
                "price_basic": basic,
                "price_product": product,
            }
        )
    return rows


def get_wb_price_before_spp(nm_id: int) -> Optional[int]:
    """
    Берёт цену до СПП из WB Discounts API для одного nmID.
    GET /api/v2/list/goods/filter?filterNmID=<nm_id>&limit=1&offset=0
    Из ответа берём sizes[0].price.
    """
    token = os.environ.get("WB_DISCOUNTS_API_TOKEN") or os.environ.get("WB_API_TOKEN")
    if not token:
        log.warning(
            "WB token is not set (WB_DISCOUNTS_API_TOKEN / WB_API_TOKEN). "
            "price_before_spp будет NULL."
        )
        return None

    headers = {"Authorization": f"Bearer {token}"}
    params = {"filterNmID": str(nm_id), "limit": 1, "offset": 0}

    try:
        r = requests.get(WB_URL, headers=headers, params=params, timeout=15)
        if r.status_code == 429:
            time.sleep(1.0)
            r = requests.get(WB_URL, headers=headers, params=params, timeout=15)

        if r.status_code >= 400:
            log.warning(
                "WB API GET failed %s, params=%s, text=%s",
                r.status_code,
                params,
                r.text,
            )
            return None

        data = r.json()
        if not data or data.get("error"):
            log.warning("WB returned error flag for nmID=%s: %s", nm_id, data)
            return None

        goods = (data.get("data") or {}).get("listGoods") or []
        if not goods:
            return None

        sizes = goods[0].get("sizes") or []
        if not sizes:
            return None

        price = sizes[0].get("price")
        if price is None:
            return None

        return int(round(float(price)))
    except Exception as e:
        log.exception("WB request failed for nmID=%s: %s", nm_id, e)
        return None


class Command(BaseCommand):
    help = "Собрать цены по всем партнёрам и сохранить снимок (price_before_spp для JKeratin)"

    def handle(self, *args, **opts):
        now = timezone.now()
        bulk: list[PriceRecord] = []

        for partner_id, partner_name in partners.items():
            rows = fetch_partner_items(partner_id)

            for r in rows:
                # price_before_spp — только для JKeratin
                price_before = None
                if partner_id == JK_PARTNER_ID:
                    price_before = get_wb_price_before_spp(r["item_id"])
                    # снизим шанс получить 429 от WB
                    time.sleep(0.15)

                bulk.append(
                    PriceRecord(
                        created_at=now,
                        partner_id=partner_id,
                        partner_name=partner_name,
                        dest="",  # храним, но на странице не показываем
                        item_id=r["item_id"],
                        item_name=r["item_name"],
                        article=r["article"],
                        price_basic=r["price_basic"],
                        price_before_spp=price_before,  # может быть None
                        price_product=r["price_product"],
                    )
                )

        if bulk:
            PriceRecord.objects.bulk_create(bulk, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"Saved {len(bulk)} rows"))
