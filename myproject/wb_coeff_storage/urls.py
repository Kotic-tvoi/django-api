from django.urls import path
from .views import wb_coeff_storage

app_name = "wb_coeff_storage"
urlpatterns = [
    path("get_coeff_storage/", wb_coeff_storage, name="get_coeff_storage"),
]
