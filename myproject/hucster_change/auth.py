from functools import wraps
from django.http import JsonResponse
from django.conf import settings

ALLOWED_KEYS = set(getattr(settings, 'HUCSTER_API_KEYS', []))

def require_api_key(view):
    @wraps(view)
    async def _wrapped(request, *args, **kwargs):
        sent_key = request.headers.get("X-API-Key")
        if not ALLOWED_KEYS or sent_key not in ALLOWED_KEYS:
            return JsonResponse({"detail": "Unauthorized"}, status=401)
        return await view(request, *args, **kwargs)
    return _wrapped
