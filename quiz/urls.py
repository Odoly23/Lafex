from django.urls import path

from . import views

urlpatterns = [
    path('latihan/quiz/', views.QuizPage, name='quiz'),
]
