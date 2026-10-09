from django.urls import path

from . import views

urlpatterns = [
    path('quiz/start/', views.APIQuizStart.as_view()),
    path('quiz/<int:attempt_id>/submit/', views.APIQuizSubmit.as_view()),
]
