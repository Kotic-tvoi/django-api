from rest_framework.decorators import api_view
from rest_framework.response import Response
from .parser import ParseWB
from .constants import partners, dest_name
from common.wb import fetch_partner_items


@api_view(["GET"])
def get_price(request):
    """Возвращает список товаров партнёра с актуальными ценами."""
    partner_id = request.GET.get("partner_id", "215484")
    try:
        partners[int(partner_id)]
    except KeyError:
        return Response({"error": "Partner not found"}, status=404)
    dest = request.GET.get("dest", str(dest_name.get("SPb", "-1275551")))
    items = fetch_partner_items(int(partner_id), dest)

    data = []
    for row in items:
        data.append({
            "id": row.get("id"),
            "name": row.get("name"),
            # "price_basic": row.get("price_basic"),
            "price_product": row.get("price_product"),
            "article": row.get("article"),
        })

    # Возвращаем красиво отформатированный JSON
    return Response(data, status=200)
