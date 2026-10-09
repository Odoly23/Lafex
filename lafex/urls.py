from django.contrib import admin
from django.urls import include, path

from billing import views as billing_views
from curriculum import views as curriculum_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/me/', billing_views.me),
    path('api/redeem/', billing_views.redeem),
    path('api/curriculum/', curriculum_views.curriculum),
    path('api/', include('tutor.api_urls')),
    path('', include('main.urls')),
    path('', include('tutor.urls')),
]

handler403 = 'main.views.error_403'
handler404 = 'main.views.error_404'
handler500 = 'main.views.error_500'
