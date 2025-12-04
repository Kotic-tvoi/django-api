from openpyxl import Workbook
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone as djtz


def generate_price_history_xlsx(queryset):
    wb = Workbook()
    ws = wb.active
    ws.title = f"price_history"

    headers = [
        "Дата создания",
        "id партнёра",
        "Партнёр",
        "Артикул WB",
        "Наш Артикул",
        "Название товара",
        "Цена до СПП",
        "Конечная цены",
    ]
    ws.append(headers)

    for r in queryset.iterator(chunk_size=2000):
        dt_local = djtz.localtime(r.created_at)
        dt_naive = dt_local.replace(tzinfo=None)

        ws.append([
            dt_naive,
            r.partner_id,
            r.partner_name,
            r.item_id,
            r.article,
            r.item_name,
            r.price_before_spp,
            r.price_product,

        ])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="price_history.xlsx"'
    return response
