from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from dotenv import dotenv_values, set_key
from openpyxl import Workbook
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .constants import partners, dest_name
from common.wb import fetch_partner_items


ENV_PATH = Path(settings.BASE_DIR) / ".env"


def normalize_bearer(value: str) -> str:
    value = (value or "").strip().strip('"').strip("'")

    if value.lower().startswith("bearer "):
        value = value.split(" ", 1)[1].strip()

    return value


def get_internal_token_from_env() -> str:
    values = dotenv_values(ENV_PATH)
    return values.get("PARSER_INTERNAL_TOKEN", "") or ""


@api_view(["POST"])
def update_wb_auth(request):
    """
    Обновляет WB_COOKIE и WB_BEARER на сервере.
    Cookie и bearer передаются только в теле POST-запроса, не в URL.
    """
    internal_token = request.headers.get("X-Internal-Token", "")
    expected_token = get_internal_token_from_env()

    if not expected_token or internal_token != expected_token:
        return Response(
            {"error": "Unauthorized"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    cookie = (request.data.get("cookie") or "").strip()
    bearer = normalize_bearer(
        request.data.get("bearer")
        or request.data.get("authorization")
        or ""
    )

    if not cookie:
        return Response(
            {"error": "cookie is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not bearer:
        return Response(
            {"error": "bearer or authorization is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "x_wbaas_token=" not in cookie:
        return Response(
            {"error": "cookie does not contain x_wbaas_token"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not ENV_PATH.exists():
        ENV_PATH.write_text("", encoding="utf-8")

    set_key(str(ENV_PATH), "WB_COOKIE", cookie, quote_mode="always")
    set_key(str(ENV_PATH), "WB_BEARER", bearer, quote_mode="always")

    return Response(
        {
            "status": "ok",
            "message": "WB auth updated",
            "cookie_length": len(cookie),
            "bearer_length": len(bearer),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def get_price(request):
    """Возвращает список товаров партнёра с актуальными ценами."""
    partner_id = request.GET.get("partner_id", "215484")

    try:
        partners[int(partner_id)]
    except KeyError:
        return Response({"error": "Partner not found"}, status=404)

    dest = request.GET.get("dest", str(dest_name.get("Москва", "1259571021")))
    items = fetch_partner_items(int(partner_id), dest)

    data = []

    for row in items:
        data.append({
            "id": row.get("id"),
            "name": row.get("name"),
            "price_product": row.get("price_product"),
            "article": row.get("article"),
        })

    return Response(data, status=200)


@api_view(["GET"])
def get_price_excel(request):
    """Возвращает Excel с товарами партнёра."""
    partner_id = request.GET.get("partner_id", "215484")

    try:
        partners[int(partner_id)]
    except KeyError:
        return Response({"error": "Partner not found"}, status=404)

    dest = request.GET.get("dest", str(dest_name.get("Москва", "1259571021")))
    items = fetch_partner_items(int(partner_id), dest)

    wb = Workbook()
    ws = wb.active
    ws.title = "Prices"

    ws.append([
        "ID",
        "Название",
        "Цена",
    ])

    for row in items:
        ws.append([
            row.get("id"),
            row.get("name"),
            row.get("price_product"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    filename = f"prices_{partners[int(partner_id)]}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response