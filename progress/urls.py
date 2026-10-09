from django.urls import path

from . import views

urlpatterns = [
    path('profil/', views.ProfilePage, name='profile'),
    path('sertifikat/<str:code>/', views.CertificatePage, name='certificate'),
]
