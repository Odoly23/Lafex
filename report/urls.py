from django.urls import path

from .views import pages

urlpatterns = [
    path('', pages.Dashboard, name='dashboard'),
]
