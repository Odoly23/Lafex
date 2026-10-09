import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from config.decorators import ALL_ROLES, allowed_users, unauthenticated_user
from config.user_utils import user_group

# Berkas yang dicache PWA agar aplikasi terbuka cepat dan review bisa offline.
SHELL_STATIC = [
    'main/css/app.css',
    'main/js/common.js', 'main/js/login.js', 'main/js/home.js',
    'main/js/mission.js', 'main/js/review.js',
    'main/images/lafaek.png', 'main/images/icon-192.png', 'main/images/icon-512.png',
    'main/images/apple-touch-icon.png',
]


@unauthenticated_user
@ensure_csrf_cookie
def LoginPage(request):
	return render(request, 'home/login.html', {'page': 'login', 'title': 'Tama'})


@login_required
@allowed_users(allowed_roles=ALL_ROLES)
@ensure_csrf_cookie
def HomePage(request):
	context = {'group': user_group(request.user), 'page': 'home', 'title': 'Lafex'}
	return render(request, 'home/home.html', context)


def manifest(request):
	data = {
        'name': 'Lafex', 'short_name': 'Lafex', 'lang': 'tet',
        'description': 'Lafaek, tutór Inglés ba ema Timor-Leste.',
        'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': '#fafaf7', 'theme_color': '#0b6b3a',
        'icons': [
            {'src': static('main/images/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': static('main/images/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
            {'src': static('main/images/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
	return HttpResponse(json.dumps(data), content_type='application/manifest+json')


@never_cache
def service_worker(request):
	resp = render(request, 'main/sw.js', {
        'version': settings.ASSET_VERSION, 'urls': [static(p) for p in SHELL_STATIC],
    }, content_type='text/javascript; charset=utf-8')
	resp['Service-Worker-Allowed'] = '/'
	return resp


def error_403(request, exception=None):
	return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
	return render(request, 'home/404.html', status=404)


def error_500(request):
	# Halaman statis tanpa pemroses konteks: kesalahan 500 bisa berasal dari sana.
	from django.template import loader
	return HttpResponse(loader.render_to_string('home/500.html'), status=500)
