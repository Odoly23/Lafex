from django.urls import path

from . import views

urlpatterns = [
    path('sessions/', views.start),
    path('sessions/<int:session_id>/turn/', views.turn),
    path('sessions/<int:session_id>/finish/', views.finish),
    path('review/', views.review),
]
