from django.urls import path

from .views import get_price, get_price_excel, update_wb_auth


app_name = "get_price"

urlpatterns = [
    path("get_price/", get_price, name="get_price"),
    path("get_price_excel/", get_price_excel),
    path("update_wb_auth/", update_wb_auth, name="update_wb_auth"),
]