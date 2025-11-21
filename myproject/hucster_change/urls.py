from django.urls import path
from . import views

urlpatterns = [
    path('', views.hucster_page, name='hucster_page'),
    path('run-all/ozon/', views.run_all_ozon, name='run_all_ozon'),
    path('run-all/wb/', views.run_all_wb, name='run_all_wb'),
    path('run-selected/', views.run_selected, name='run_selected'),
]
