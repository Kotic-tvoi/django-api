from rest_framework.decorators import api_view
from rest_framework.response import Response
from .parser import ParseWB
from .constants import partners, dest_name
from common.wb import fetch_partner_items
from openpyxl import Workbook
from django.http import HttpResponse


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


@api_view(["GET"])
def get_price_excel(request):
    """Возвращает Excel с товарами партнёра."""
    partner_id = request.GET.get("partner_id", "215484")
    try:
        partners[int(partner_id)]
    except KeyError:
        return Response({"error": "Partner not found"}, status=404)

    dest = request.GET.get("dest", str(dest_name.get("SPb", "-1275551")))
    items = fetch_partner_items(int(partner_id), dest)

    # ===== Excel =====
    wb = Workbook()
    ws = wb.active
    ws.title = "Prices"

    # Заголовки
    ws.append([
        "ID",
        "Название",
        "Цена",
    ])

    # Данные
    for row in items:
        ws.append([
            row.get("id"),
            row.get("name"),
            row.get("price_product"),
        ])

    # HTTP Ответ
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"prices_{partners[int(partner_id)]}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response