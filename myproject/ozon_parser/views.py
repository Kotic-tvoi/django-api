# views.py

from django.http import JsonResponse
from .ozon import parse_ozon_many  # <-- берём многопоточный вариант


def ozon_parser(request):
    raw = request.GET.get("articles")

    if not raw:
        return JsonResponse({"error": "articles required"}, status=400)

    articles = [art.strip() for art in raw.split(",") if art.strip()]

    # 🔥 многопоточный парсинг (3 потока как в твоём коде)
    results = parse_ozon_many(articles, max_threads=3)

    return JsonResponse({"results": results}, safe=False)
