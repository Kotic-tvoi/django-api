from rest_framework.decorators import api_view
from rest_framework.response import Response
from .ozon import parse_article


@api_view(["GET"])
def ozon_price(request):
    article = request.GET.get("article")

    if not article:
        return Response({"error": "article required"}, status=400)

    data = parse_article(article)
    return Response(data)
