import requests
from django.http import JsonResponse


LOCAL_PROXY_URL = "http://192.168.35.83:9000"   # ← ТВОЙ ЛОКАЛЬНЫЙ IP


def proxy_to_local(request):
    partner_id = request.GET.get("partner_id")
    dest = request.GET.get("dest")

    if not partner_id or not dest:
        return JsonResponse({"error": "Missing partner_id or dest"}, status=400)

    url = f"{LOCAL_PROXY_URL}/parser/get_price/?partner_id={partner_id}&dest={dest}"

    try:
        response = requests.get(url, timeout=30)
        return JsonResponse(response.json(), safe=False)

    except Exception as e:
        return JsonResponse({"error": f"Proxy error: {str(e)}"}, status=500)
