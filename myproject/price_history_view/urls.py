from django.urls import path
from .views import price_history_view

app_name = "price_history_view"
urlpatterns = [
    path("price-history/", price_history_view, name="price_history"),
]
