from django.contrib import admin
from django.urls import include, path

from billing import views as billing_views
from curriculum import views as curriculum_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/me/', billing_views.me),
    path('api/redeem/', billing_views.redeem),
    path('api/curriculum/', curriculum_views.curriculum),
    path('api/', include('tutor.urls')),
    path('', include('frontend.urls')),
]
