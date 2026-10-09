from django.urls import path

from .views import pages

urlpatterns = [
    path('mission/<slug:slug>/', pages.MissionPage, name='mission'),
    path('review/', pages.ReviewPage, name='review'),
    path('belajar/ngobrol/', pages.ChatPage, name='chat'),
    path('belajar/situasaun/', pages.SituationsPage, name='situations'),
    path('belajar/grammar/', pages.GrammarPage, name='grammar'),
]
