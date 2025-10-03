from django.urls import path
from .views import send  # единый эндпоинт

urlpatterns = [
    path('send/', send, name='hucster_send'),
]
