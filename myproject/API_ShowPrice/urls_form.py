from django.urls import path
from .views_extra import price_history_view

urlpatterns = [
    path("price-history/", price_history_view, name="price_history"),
]
