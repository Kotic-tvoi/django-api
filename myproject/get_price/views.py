from rest_framework.decorators import api_view
from rest_framework.response import Response
from .parser import ParseWB, partners, dest_name
from common.wb import fetch_partner_items

@api_view(["GET"])
def get_price(request):
    partner_id = request.GET.get("partner_id", "215484")
    try:
        partners[int(partner_id)]
    except KeyError:
        return Response({"error": "Partner not found"}, status=404)

    dest = request.GET.get("dest", str(dest_name["Москва"]))
    seller_id = int(partner_id)

    items = ParseWB(f"https://www.wildberries.ru/seller/{seller_id}", dest=dest).get_items()

    data = []
    for row in fetch_partner_items(partner_id, dest):
        data.append([row["item_id"], row["item_name"], row["price_basic"], row["price_product"]])
    return Response(data)


