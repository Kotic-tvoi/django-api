# get_price/common.py
from get_price.parser import ParseWB

def fetch_partner_items(partner_id: int, dest: str):
    """
    Возвращает нормализованный список товаров партнёра:
    id, name, цены (рубли), буквенный артикул.
    """
    items = ParseWB(f"https://www.wildberries.ru/seller/{partner_id}", dest=dest).get_items()
    rows = []
    for p in items.products:
        try:
            basic = int(p.sizes[0].price.basic / 100)
            product = int(p.sizes[0].price.product / 100)
        except Exception:
            continue
        vendor = getattr(p, "vendorCode", "") or getattr(p, "supplierVendorCode", "") or ""
        rows.append({
            "item_id": p.id,
            "item_name": p.name,
            "price_basic": basic,
            "price_product": product,
            "article": vendor,
        })
    return rows
