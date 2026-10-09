from django.urls import path

from .views import api

urlpatterns = [
    path('sessions/', api.APIStart.as_view()),
    path('sessions/<int:session_id>/turn/', api.APITurn.as_view()),
    path('sessions/<int:session_id>/finish/', api.APIFinish.as_view()),
    path('review/', api.APIReview.as_view()),
]
