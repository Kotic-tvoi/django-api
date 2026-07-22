from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView


home_view = TemplateView.as_view(
    template_name="home.html",
    extra_context={
        "price_history_enabled": settings.PRICE_HISTORY_VIEW_ENABLED,
        "hucster_change_enabled": settings.HUCSTER_CHANGE_ENABLED,
    },
)

urlpatterns = [
    path("", home_view, name="home"),
    path("admin/", admin.site.urls),
    path("parser/", include("get_price.urls", namespace="get_price")),
    # path("storage/", include("wb_coeff_storage.urls", namespace="wb_coeff_storage")),
    path("ozon_parser/", include("ozon_parser.urls")),
]

# Код приложений остаётся в проекте, но URL подключаются только при включении флагов.
if settings.PRICE_HISTORY_VIEW_ENABLED:
    urlpatterns.append(
        path("reports/", include("price_history_view.urls", namespace="price_history_view"))
    )

if settings.HUCSTER_CHANGE_ENABLED:
    urlpatterns.append(path("hucster/", include("hucster_change.urls")))
