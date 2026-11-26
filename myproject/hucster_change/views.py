import json
import re
from asyncio import run

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .auth import require_api_key
from .constants import product_keys, MAX_RETRIES, CONCURRENCY


async def _run_many_keys(keys, mp_key, concurrency, max_retries):
    # Playwright is an optional dependency: import it only when Huckster is enabled.
    from .runner import run_many_keys_with_back

    return await run_many_keys_with_back(
        keys,
        mp_key=mp_key,
        concurrency=concurrency,
        max_retries=max_retries,
    )


def hucster_page(request):
    """Главная страница Хакстера."""
    return render(request, "hucster_change/index.html")


def run_all_ozon(request):
    keys = list(product_keys.keys())
    results = run(_run_many_keys(
        keys,
        mp_key="ozon",
        concurrency=CONCURRENCY,
        max_retries=MAX_RETRIES,
    ))
    return JsonResponse(results, safe=False)


def run_all_wb(request):
    keys = list(product_keys.keys())
    results = run(_run_many_keys(
        keys,
        mp_key="wb",
        concurrency=CONCURRENCY,
        max_retries=MAX_RETRIES,
    ))
    return JsonResponse(results, safe=False)


@csrf_exempt
def run_selected(request):
    if request.method != "POST":
        return JsonResponse({"error": "Метод не POST"}, status=405)

    text = request.POST.get("keys", "")
    mp = request.POST.get("mp", "").strip().lower()

    # Ручная форма принимает внутренние артикулы из product_keys.
    articles = [article.strip() for article in text.splitlines() if article.strip()]
    article_to_key = {
        article.casefold(): key
        for key, article in product_keys.items()
    }
    keys = [
        article_to_key[article.casefold()]
        for article in articles
        if article.casefold() in article_to_key
    ]

    if mp not in {"wb", "ozon"}:
        return JsonResponse({"error": "mp должен быть wb или ozon"}, status=400)

    if not keys:
        return JsonResponse({"error": "Не найдено ни одного артикула"}, status=400)

    results = run(_run_many_keys(
        keys,
        mp_key=mp,
        concurrency=3,
        max_retries=3,
    ))
    return JsonResponse(results, safe=False)


def _resolve_requested_keys(raw_values):
    """Преобразует Huckster key или внутренний артикул в ключ из product_keys."""
    if isinstance(raw_values, str):
        values = re.split(r"[\\n,;]+", raw_values)
    elif isinstance(raw_values, list):
        values = raw_values
    else:
        return [], [], ["Передайте key/keys строкой или массивом"]

    article_to_key = {
        str(article).strip().casefold(): key
        for key, article in product_keys.items()
    }

    resolved = []
    unknown = []

    for value in values:
        if value is None:
            continue

        value = str(value).strip()
        if not value:
            continue

        if value in product_keys:
            key = value
        else:
            key = article_to_key.get(value.casefold())

        if key is None:
            unknown.append(value)
        elif key not in resolved:
            resolved.append(key)

    return resolved, unknown, []


@csrf_exempt
@require_api_key
async def send_to_hucster(request):
    """
    API для отправки артикулов на проверку Huckster.

    POST /hucster/send/
    Headers: X-API-Key: <ключ из HUCSTER_API_KEYS>
    JSON: {"mp": "wb", "key": "ColdBTX150"}
    Также поддерживаются массивы: {"mp": "ozon", "keys": ["ColdBTX150", "..."]}.
    В key/keys можно передать 32-символьный Huckster key или внутренний артикул
    из product_keys.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Метод не POST"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Ожидается корректный JSON"}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "JSON должен содержать объект"}, status=400)

    mp = str(payload.get("mp", "")).strip().lower()
    if mp not in {"wb", "ozon"}:
        return JsonResponse({"error": "mp должен быть wb или ozon"}, status=400)

    raw_values = payload.get("keys")
    if raw_values is None:
        raw_values = payload.get("key")
    if raw_values is None:
        raw_values = payload.get("articles")
    if raw_values is None:
        raw_values = payload.get("article")

    keys, unknown, errors = _resolve_requested_keys(raw_values)

    if errors:
        return JsonResponse({"error": errors[0]}, status=400)
    if unknown:
        return JsonResponse({
            "error": "Не удалось сопоставить часть артикулов с ключами Huckster",
            "unknown": unknown,
        }, status=400)
    if not keys:
        return JsonResponse({"error": "Список артикулов пуст"}, status=400)

    try:
        results = await _run_many_keys(
            keys,
            mp_key=mp,
            concurrency=CONCURRENCY,
            max_retries=MAX_RETRIES,
        )
    except Exception as exc:
        return JsonResponse({
            "error": "Не удалось выполнить проверку Huckster",
            "details": str(exc),
        }, status=502)

    return JsonResponse({
        "ok": True,
        "mp": mp,
        "requested": len(keys),
        "articles": [product_keys[key] for key in keys],
        "results": results,
    })
