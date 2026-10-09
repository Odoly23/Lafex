from django.urls import path

from . import views

urlpatterns = [
    path('stats/', views.APIStats.as_view()),
    path('sesaun-daily/', views.APISesaunDaily.as_view()),
    path('levels/', views.APILevels.as_view()),
    path('misaun/', views.APIMisaun.as_view()),
    path('vaucher/', views.APIVaucher.as_view()),
]
