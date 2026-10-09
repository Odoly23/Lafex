from django.contrib import admin
from django.urls import include, path

from billing import views as billing_views
from curriculum import views as curriculum_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/me/', billing_views.APIMe.as_view()),
    path('api/redeem/', billing_views.APIRedeem.as_view()),
    path('api/curriculum/', curriculum_views.APICurriculum.as_view()),
    path('api/report/', include('report.api.urls')),
    path('api/', include('progress.api_urls')),
    path('api/', include('vocab.api_urls')),
    path('api/', include('quiz.api_urls')),
    path('api/', include('pronounce.api_urls')),
    path('api/', include('tutor.api_urls')),
    path('', include('main.urls')),
    path('', include('tutor.urls')),
    path('', include('progress.urls')),
    path('', include('vocab.urls')),
    path('', include('quiz.urls')),
    path('', include('pronounce.urls')),
    path('staff/', include('report.urls')),
    path('staff/siswa/', include('users.staff_urls')),
    path('staff/vaucher/', include('billing.staff_urls')),
    path('staff/misaun/', include('curriculum.staff_urls')),
]

handler403 = 'main.views.error_403'
handler404 = 'main.views.error_404'
handler500 = 'main.views.error_500'
