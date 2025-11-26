from django.urls import path
from .views import ozon_price

app_name = "ozon_price"
urlpatterns = [
    path("get_price/", ozon_price, name="get_price"),
]
