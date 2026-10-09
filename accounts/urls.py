from django.urls import path

from . import views

urlpatterns = [
    path('request/', views.request_code),
    path('verify/', views.verify),
    path('logout/', views.logout_view),
]
