from django.urls import path

from .views import api

urlpatterns = [
    path('sessions/', api.start),
    path('sessions/<int:session_id>/turn/', api.turn),
    path('sessions/<int:session_id>/finish/', api.finish),
    path('review/', api.review),
]
