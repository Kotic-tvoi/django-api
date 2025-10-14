from rest_framework.decorators import api_view
from rest_framework.response import Response
from .services import get_wb_coef_storage

@api_view(["GET"])
def wb_coeff_storage(request):
    warehouse_id = request.GET.get("warehouse_id")
    data = get_wb_coef_storage(warehouse_id)
    return Response(data)
