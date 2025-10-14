from django.urls import path
from .views import get_price

app_name = "get_price"
urlpatterns = [
    path("get_price/", get_price, name="get_price"),
]
