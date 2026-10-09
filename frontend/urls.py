from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('mission/<slug:slug>/', views.mission_page, name='mission'),
    path('review/', views.review_page, name='review'),
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
]
