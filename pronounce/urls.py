from django.urls import path

from . import views

urlpatterns = [
    path('latihan/pronunciation/', views.PronPage, name='pron'),
]
