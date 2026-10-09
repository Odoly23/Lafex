from django.urls import path

from . import views

urlpatterns = [
    path('vocab/', views.APIVocabCategories.as_view()),
    path('vocab/known/', views.APIVocabKnown.as_view()),
    path('vocab/<slug:slug>/', views.APIVocabStudy.as_view()),
]
