
from django.shortcuts import render
from django.http import JsonResponse
from asyncio import run
from .runner import run_many_keys_with_back
from .constants import product_keys, MAX_RETRIES, CONCURRENCY
from django.views.decorators.csrf import csrf_exempt

def hucster_page(request):
    """Главная страница Хакстера"""
    return render(request, "hucster_change/index.html")


def run_all_ozon(request):
    keys = list(product_keys.keys())

    results = run(run_many_keys_with_back(
        keys, 
        mp_key="ozon", 
        concurrency=CONCURRENCY, 
        max_retries=MAX_RETRIES
    ))

    return JsonResponse(results, safe=False)


def run_all_wb(request):
    keys = list(product_keys.keys())

    results = run(run_many_keys_with_back(
        keys,
        mp_key="wb", 
        concurrency=CONCURRENCY, 
        max_retries=MAX_RETRIES
    ))

    return JsonResponse(results, safe=False)


@csrf_exempt
def run_selected(request):
    if request.method == "POST":
        text = request.POST.get("keys", "")
        mp = request.POST.get("mp")

        # Разбираем ввод через Enter
        articles = [a.strip() for a in text.splitlines() if a.strip()]

        # ищем ключи по названиям
        keys = [
            key32 for key32, name in product_keys.items()
            if name in articles
        ]

        results = run(run_many_keys_with_back(
            keys,
            mp_key=mp,
            concurrency=3,
            max_retries=3
        ))

        return JsonResponse(results, safe=False)

    return JsonResponse({"error": "Метод не POST"})
