from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .parser import ParseWB, partners
from .services import get_wb_coef_storage

@api_view(['GET'])
def get_price(request):
    partner_id = request.GET.get('partner_id', '215484')
    try:
        partners[int(partner_id)]
    except KeyError:
        return Response({"error": "Partner not found"}, status=404)

    parser = ParseWB(f"https://www.wildberries.ru/seller/{partner_id}?brand=279103")
    items_info = parser.get_items()

    data = [['id', 'название', 'начальная цена', 'конечная цена без WB карты']]
    for product in items_info.products:
        row = [
            product.id,
            product.name,
            int(product.sizes[0].price.basic / 100),
            int(product.sizes[0].price.product / 100)
        ]
        data.append(row)

    return Response(data)


@api_view(['GET'])
def wb_coeff_storage(request):
    # Можно получить warehouseID из запроса: /?warehouse_id=12345
    warehouse_id = request.GET.get("warehouse_id")
    data = get_wb_coef_storage(warehouse_id)

    # Вернём JSON-ответ пользователю
    return Response(data)
