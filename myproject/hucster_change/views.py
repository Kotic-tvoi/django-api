import json
import re
from asyncio import run

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .auth import require_api_key
from .constants import product_keys, MAX_RETRIES, CONCURRENCY


HUCKSTER_KEY_RE = re.compile(r"^[a-f0-9]{32}$", re.IGNORECASE)


async def _run_many_keys(keys, mp_key, concurrency, max_retries):
    # Playwright is optional until the Huckster module is enabled.
    from .runner import run_many_keys_with_back

    return await run_many_keys_with_back(
        keys,
        mp_key=mp_key,
        concurrency=concurrency,
        max_retries=max_retries,
    )


def hucster_page(request):
    """Панель ручной отправки товаров на проверку Huckster."""
    return render(request, "hucster_change/index.html")


def run_all_ozon(request):
    keys = list(product_keys.keys())
    results = run(_run_many_keys(
        keys, mp_key="ozon", concurrency=CONCURRENCY, max_retries=MAX_RETRIES
    ))
    return JsonResponse(results, safe=False)


def run_all_wb(request):
    keys = list(product_keys.keys())
    results = run(_run_many_keys(
        keys, mp_key="wb", concurrency=CONCURRENCY, max_retries=MAX_RETRIES
    ))
    return JsonResponse(results, safe=False)


def _resolve_requested_keys(raw_values):
    """Принимает внутренние uid, готовые 32-символьные id или массив значений."""
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
        elif value.casefold() in article_to_key:
            key = article_to_key[value.casefold()]
        elif HUCKSTER_KEY_RE.fullmatch(value):
            # Ключи из актуального Catalog_Get могут отсутствовать в constants.py.
            key = value
        else:
            unknown.append(value)
            continue

        if key not in resolved:
            resolved.append(key)

    return resolved, unknown, []


def _extract_catalog_labels(payload):
    """Читает uid -> id из элементов Catalog_Get, если они переданы клиентом."""
    labels = {}

    items = payload.get("items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("id", "")).strip()
            uid = str(item.get("uid", "")).strip()
            if HUCKSTER_KEY_RE.fullmatch(key) and uid:
                labels[key] = uid

    explicit_labels = payload.get("labels")
    if isinstance(explicit_labels, dict):
        for key, uid in explicit_labels.items():
            key = str(key).strip()
            uid = str(uid).strip()
            if HUCKSTER_KEY_RE.fullmatch(key) and uid:
                labels[key] = uid

    return labels


def _attach_article_labels(results, labels):
    for result in results:
        key = result.get("key")
        if key in labels:
            result["article"] = labels[key]
        elif key in product_keys:
            result["article"] = product_keys[key]
    return results


@csrf_exempt
def run_selected(request):
    """Веб-форма: uid или Huckster id, по одному значению на строку."""
    if request.method != "POST":
        return JsonResponse({"error": "Метод не POST"}, status=405)

    mp = request.POST.get("mp", "").strip().lower()
    if mp not in {"wb", "ozon"}:
        return JsonResponse({"error": "mp должен быть wb или ozon"}, status=400)

    keys, unknown, errors = _resolve_requested_keys(request.POST.get("keys", ""))
    if errors:
        return JsonResponse({"error": errors[0]}, status=400)
    if unknown:
        return JsonResponse({
            "error": "Не удалось распознать часть uid или Huckster id",
            "unknown": unknown,
        }, status=400)
    if not keys:
        return JsonResponse({"error": "Не найдено ни одного артикула"}, status=400)

    results = run(_run_many_keys(
        keys, mp_key=mp, concurrency=CONCURRENCY, max_retries=MAX_RETRIES
    ))
    return JsonResponse({
        "ok": True,
        "mp": mp,
        "requested": len(keys),
        "results": results,
    })


@csrf_exempt
@require_api_key
async def send_to_hucster(request):
    """
    POST /hucster/send/
    Headers: X-API-Key: <значение из HUCSTER_API_KEYS>

    Поддерживаемые форматы:
      {"mp":"wb", "keys":["<32-char-id>", "..."]}
      {"mp":"ozon", "items":[{"uid":"маска_7Seconds","id":"<32-char-id>"}]}
      {"mp":"wb", "key":"ColdBTX150"}

    items/labels нужны, чтобы вернуть uid в результатах. id передаётся
    непосредственно в существующий Playwright runner как хвост URL каталога.
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

    labels = _extract_catalog_labels(payload)

    if raw_values is None and isinstance(payload.get("items"), list):
        raw_values = [
            item.get("id")
            for item in payload["items"]
            if isinstance(item, dict)
        ]

    keys, unknown, errors = _resolve_requested_keys(raw_values)

    if errors:
        return JsonResponse({"error": errors[0]}, status=400)
    if unknown:
        return JsonResponse({
            "error": "Не удалось сопоставить часть uid или Huckster id",
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

    _attach_article_labels(results, labels)

    return JsonResponse({
        "ok": True,
        "mp": mp,
        "requested": len(keys),
        "articles": [
            labels.get(key, product_keys.get(key, key))
            for key in keys
        ],
        "results": results,
    })
