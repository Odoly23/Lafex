from django.urls import path

from . import views

urlpatterns = [
    path('pron/start/', views.APIPronStart.as_view()),
    path('pron/score/', views.APIPronScore.as_view()),
]
