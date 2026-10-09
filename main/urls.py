from django.urls import path

from . import views

urlpatterns = [
    path('', views.HomePage, name='home'),
    path('login/', views.LoginPage, name='login'),
    # Nama URL yang dicari allauth saat alur login sosial (kita tidak memakai tampilan akun bawaannya).
    path('accounts/login/', views.LoginPage, name='account_login'),
    path('accounts/signup/', views.SignupRedirect, name='account_signup'),
    path('accounts/inactive/', views.AccountInactive, name='account_inactive'),
    path('accounts/login/cancelled/', views.SocialCancelled, name='socialaccount_login_cancelled'),
    path('accounts/login/error/', views.SocialError, name='socialaccount_login_error'),
    path('accounts/3rdparty/signup/', views.SignupRedirect, name='socialaccount_signup'),
    path('manifest.webmanifest', views.manifest),
    path('sw.js', views.service_worker),
]
