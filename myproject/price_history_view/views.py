from django.shortcuts import render
from django.core.paginator import Paginator
# from django.http import HttpResponse
from django.utils.http import urlencode

from .models import PriceRecord
from .forms import PriceFilterForm
from common.constants import partners
from .exporters.xlsx_export import generate_price_history_xlsx


def price_history_view(request):
    form = PriceFilterForm(request.GET or None)
    qs = PriceRecord.objects.all().order_by("-created_at", "partner_id", "item_id")

    # --- ФИЛЬТРЫ ---
    if form.is_valid():
        partner = form.cleaned_data.get("partner")
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")
        item_mode = form.cleaned_data.get("item_mode")
        item_ids_raw = form.cleaned_data.get("item_ids")

        if partner:
            qs = qs.filter(partner_id=int(partner))

        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        if item_mode == "selected" and item_ids_raw:
            from re import split
            try:
                ids = [int(x) for x in split(r"[\s,]+", item_ids_raw) if x.strip()]
                qs = qs.filter(item_id__in=ids)
            except:
                pass

    # --- ОПТИМИЗАЦИЯ ---
    qs = qs.only(
        "created_at", "partner_id", "partner_name",
        "item_id", "item_name", "article", "price_product", "price_before_spp"
    )

    # --- EXPORT XLSX ---
    if request.GET.get("export") == "xlsx":
        return generate_price_history_xlsx(qs)

    # --- ПАГИНАЦИЯ ---
    paginator = Paginator(qs, 200)
    page_obj = paginator.get_page(request.GET.get("page"))
    # Чтобы не терять фильтрацию с пагинацией
    params = request.GET.copy()
    params.pop("page", None)
    query_tail = urlencode(params, doseq=True)

    return render(
        request,
        "price_history_view/price_history.html",
        {
            "form": form,
            "rows": page_obj,
            "query_tail": f"&{query_tail}" if query_tail else "",
        }
    )
