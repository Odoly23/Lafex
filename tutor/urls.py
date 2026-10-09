from django.urls import path

from .views import pages

urlpatterns = [
    path('mission/<slug:slug>/', pages.MissionPage, name='mission'),
    path('review/', pages.ReviewPage, name='review'),
]
