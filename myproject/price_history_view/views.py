from django.shortcuts import render
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone as djtz
import csv, re

from .models import PriceRecord
from .forms import PriceFilterForm


def price_history_view(request):
    form = PriceFilterForm(request.GET or None)
    qs = PriceRecord.objects.all()

    # ----- фильтрация -----
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
            parts = [p.strip() for p in re.split(r"[\s,]+", item_ids_raw) if p.strip()]
            try:
                ids = [int(p) for p in parts]
                qs = qs.filter(item_id__in=ids)
            except Exception:
                # некорректный ввод ID — просто не фильтруем
                pass

    qs = qs.select_related(None).only(
        "created_at", "partner_id", "dest", "item_id", "item_name", "price_basic", "price_product"
    )

    # ----- экспорт -----
    export = (request.GET.get("export") or "").strip().lower()

    if export == "xlsx":
        try:
            from openpyxl import Workbook
        except Exception:
            return HttpResponse(
                "openpyxl not installed. Run: pip install openpyxl",
                content_type="text/plain; charset=utf-8",
                status=500,
            )

        wb = Workbook()
        ws = wb.active
        ws.title = "price_history"
        headers = ["created_at", "partner_id", "dest", "item_id", "item_name", "price_basic", "price_product"]
        ws.append(headers)

        for r in qs.iterator(chunk_size=2000):
            # Excel не поддерживает tz-aware datetime — убираем tzinfo
            dt_local = djtz.localtime(r.created_at)
            dt_naive = dt_local.replace(tzinfo=None)
            ws.append([dt_naive, r.partner_id, r.dest, r.item_id, r.item_name, r.price_basic, r.price_product])

        from io import BytesIO
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = 'attachment; filename="price_history.xlsx"'
        return resp

    if export == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="price_history.csv"'

        # BOM — чтобы Excel корректно понял UTF-8 и кириллицу
        resp.write("\ufeff")
        writer = csv.writer(resp)  # при необходимости можно delimiter=';'
        writer.writerow(["created_at", "partner_id", "dest", "item_id", "item_name", "price_basic", "price_product"])

        for r in qs.iterator(chunk_size=2000):
            dt_str = djtz.localtime(r.created_at).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([dt_str, r.partner_id, r.dest, r.item_id, r.item_name, r.price_basic, r.price_product])

        return resp

    # ----- обычный рендер таблицы -----
    paginator = Paginator(qs, 200)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "price_history_view/price_history.html", {"form": form, "rows": page_obj})