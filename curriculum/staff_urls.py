from django.urls import path

from . import staff_views

urlpatterns = [
    path('', staff_views.MissionList, name='mission_list'),
]
