import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from curriculum.models import Mission

# Berkas yang dicache PWA agar aplikasi terbuka cepat dan review bisa offline.
SHELL_STATIC = [
    'frontend/css/app.css',
    'frontend/js/common.js', 'frontend/js/login.js', 'frontend/js/home.js',
    'frontend/js/mission.js', 'frontend/js/review.js',
    'frontend/img/lafaek.png', 'frontend/img/icon-192.png', 'frontend/img/icon-512.png',
    'frontend/img/apple-touch-icon.png',
]


@ensure_csrf_cookie
def login_page(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'frontend/login.html')


@login_required
@ensure_csrf_cookie
def home(request):
    return render(request, 'frontend/home.html')


@login_required
@ensure_csrf_cookie
def mission_page(request, slug):
    mission = get_object_or_404(Mission, slug=slug, active=True)
    return render(request, 'frontend/mission.html', {'mission': mission})


@login_required
@ensure_csrf_cookie
def review_page(request):
    # Sengaja tanpa data pengguna di HTML: berkas ini dicache dan data diambil lewat API / IndexedDB.
    return render(request, 'frontend/review.html')


def manifest(request):
    data = {
        'name': 'Lafex', 'short_name': 'Lafex', 'lang': 'tet',
        'description': 'Lafaek, tutór Inglés ba ema Timor-Leste.',
        'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': '#fafaf7', 'theme_color': '#0b6b3a',
        'icons': [
            {'src': static('frontend/img/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': static('frontend/img/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
            {'src': static('frontend/img/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return HttpResponse(json.dumps(data), content_type='application/manifest+json')


@never_cache
def service_worker(request):
    resp = render(request, 'frontend/sw.js', {
        'version': settings.ASSET_VERSION, 'urls': [static(p) for p in SHELL_STATIC],
    }, content_type='text/javascript; charset=utf-8')
    resp['Service-Worker-Allowed'] = '/'
    return resp
