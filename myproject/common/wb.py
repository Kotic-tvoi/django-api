from get_price.parser import ParseWB

def fetch_partner_items(partner_id: int, dest: str):
    parser = ParseWB(f"https://www.wildberries.ru/seller/{partner_id}", dest=dest)
    items_obj = parser.get_items()
    products = getattr(items_obj, "products", [])

    rows = []
    for p in products:
        try:
            basic = int(p.sizes[0].price.basic / 100)
            product = int(p.sizes[0].price.product / 100)
        except Exception:
            continue
        article = ""
        rows.append({
            "id": p.id,
            "name": p.name,
            "price_basic": basic,
            "price_product": product,
            "article": article,
        })
    return rows