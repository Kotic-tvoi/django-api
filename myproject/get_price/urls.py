from django.urls import path
from .views import get_price, get_price_excel

app_name = "get_price"
urlpatterns = [
    path("get_price/", get_price, name="get_price"),
    path("get_price_excel/", get_price_excel),
]
