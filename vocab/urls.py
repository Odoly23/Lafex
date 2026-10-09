from django.urls import path

from . import views

urlpatterns = [
    path('belajar/kosakata/', views.VocabCategories, name='vocab'),
    path('belajar/kosakata/<slug:slug>/', views.VocabStudy, name='vocab_study'),
]
