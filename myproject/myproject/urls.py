from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),  # ← главная
    path("admin/", admin.site.urls),
    path("parser/", include("get_price.urls", namespace="get_price")),
    # path("storage/", include("wb_coeff_storage.urls", namespace="wb_coeff_storage")),
    # path("reports/", include("price_history_view.urls", namespace="price_history_view")),
    # path('hucster/', include('hucster_change.urls')),
]
