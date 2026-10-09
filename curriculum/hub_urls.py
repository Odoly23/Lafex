from django.urls import path

from . import staff_views

urlpatterns = [
    path('', staff_views.MaterialHub, name='material_hub'),
]
