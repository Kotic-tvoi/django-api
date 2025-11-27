from django.urls import path
from .views import ozon_parser

app_name = "ozon_price"
urlpatterns = [
    path("get_price/", ozon_parser, name="get_price"),
]
