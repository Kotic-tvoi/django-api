from django.urls import path
from .views import get_price, wb_coeff_storage

urlpatterns = [
    path('get_price/', get_price),
    path("get_coeff_storage/", wb_coeff_storage, name="wb_coeff_storage"),
]
