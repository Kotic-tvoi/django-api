from rest_framework.decorators import api_view
from rest_framework.response import Response
from .parser import ParseWB, partners

@api_view(['GET'])
def get_data(request):
    partner_id = request.GET.get('partner_id', '215484')
    try:
        partner_name = partners[int(partner_id)]
    except KeyError:
        return Response({"error": "Partner not found"}, status=404)

    parser = ParseWB(f"https://www.wildberries.ru/seller/{partner_id}?brand=279103")
    items_info = parser.get_items()

    data = [['id', 'название', 'начальная цена', 'конечная цена без WB карты', 'конечная цена с WB картой']]
    for product in items_info.products:
        row = [
            product.id,
            product.name,
            int(product.sizes[0].price.basic / 100),
            int(product.sizes[0].price.product / 100),
            int(product.sizes[0].price.product / 100 * (100 - parser.WB_CART) / 100)
        ]
        data.append(row)

    return Response(data)
