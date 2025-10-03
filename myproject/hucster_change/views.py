import json
from typing import Any
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from .auth import require_api_key
from .runner import is_valid_key, run_once_key, run_many_keys

def _json(request: HttpRequest) -> dict[str, Any]:
    try:
        return json.loads(request.body or b"{}")
    except Exception:
        return {}

@csrf_exempt
@require_api_key
async def send(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    data = _json(request)
    mp = (data.get("mp") or "wb").lower()
    concurrency = int(data.get("concurrency") or 3)

    # режим 1: один ключ
    if isinstance(data.get("key"), str):
        key = data["key"].strip()
        if not is_valid_key(key):
            return JsonResponse({"detail": "Некорректный key: ожидаю 32-символьный hex"}, status=400)
        result = await run_once_key(key, mp)
        return JsonResponse(result, status=200)

    # режим 2: список ключей
    keys = data.get("keys")
    if isinstance(keys, list) and keys:
        cleaned = [str(k).strip() for k in keys]
        bad = [k for k in cleaned if not is_valid_key(k)]
        if bad:
            return JsonResponse({"detail": "Некорректные ключи", "bad": bad}, status=400)
        results = await run_many_keys(cleaned, mp, concurrency=concurrency)
        return JsonResponse({"count": len(results), "results": results}, status=200)

    return JsonResponse({"detail": "Укажите 'key' (str) или 'keys' (list[str])"}, status=400)
