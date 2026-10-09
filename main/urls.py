from django.urls import path

from . import views

urlpatterns = [
    path('', views.HomePage, name='home'),
    path('login/', views.LoginPage, name='login'),
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
]
