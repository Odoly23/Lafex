import json
import re
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase

from accounts.models import User
from curriculum import seed

from .strings import TETUN
from .views import SHELL_STATIC


class PageTests(TestCase):
    def setUp(self):
        seed.run()

    def test_anonymous_is_sent_to_login(self):
        for url in ('/', '/mission/tourist-airport/', '/review/'):
            r = self.client.get(url)
            self.assertEqual((r.status_code, r['Location'].startswith('/login/')), (302, True), url)

    def test_login_page_sets_csrf_cookie(self):
        r = self.client.get('/login/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('csrftoken', r.cookies)
        self.assertContains(r, 'Tama ba Lafex')

    def test_authenticated_pages(self):
        self.client.force_login(User.objects.create_user('secret.person@x.com'))
        self.assertEqual(self.client.get('/login/').status_code, 302)
        for url in ('/', '/mission/placement/', '/mission/tourist-airport/', '/review/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertNotContains(r, 'secret.person@x.com')  # halaman dicache PWA: tanpa data pengguna
        self.assertEqual(self.client.get('/mission/nope/').status_code, 404)
        self.assertContains(self.client.get('/mission/tourist-airport/'), 'Mai iha aeroportu')

    def test_manifest(self):
        r = self.client.get('/manifest.webmanifest')
        self.assertEqual(r['content-type'], 'application/manifest+json')
        m = json.loads(r.content)
        self.assertEqual((m['display'], m['start_url']), ('standalone', '/'))
        self.assertTrue(any(i.get('purpose') == 'maskable' for i in m['icons']))

    def test_service_worker(self):
        r = self.client.get('/sw.js')
        self.assertEqual(r['content-type'], 'text/javascript; charset=utf-8')
        self.assertEqual(r['Service-Worker-Allowed'], '/')
        self.assertIn('no-cache', r['Cache-Control'])
        body = r.content.decode()
        self.assertIn('/static/frontend/js/review.js', body)
        self.assertIn("url.pathname.startsWith('/api/')", body)  # API tidak boleh dicache
        self.assertIn('!res.redirected', body)  # halaman login tidak boleh tersimpan sebagai /review/

    def test_precached_files_exist(self):
        for p in SHELL_STATIC:
            self.assertTrue(finders.find(p), p)

    def test_icons_have_right_size(self):
        import struct
        for name, size in (('icon-192.png', 192), ('icon-512.png', 512), ('icon-maskable-512.png', 512)):
            head = Path(finders.find(f'frontend/img/{name}')).read_bytes()[:24]
            self.assertEqual(head[:8], b'\x89PNG\r\n\x1a\n', name)
            self.assertEqual(struct.unpack('>II', head[16:24]), (size, size), name)


class StringsTests(TestCase):
    """Mencegah salah ketik kunci teks: setiap T.xxx di templat dan JS harus ada di strings.py."""

    def test_all_referenced_keys_exist(self):
        root = Path(__file__).parent
        missing = set()
        for f in list((root / 'templates').rglob('*.html')) + list((root / 'static/frontend/js').glob('*.js')):
            text = f.read_text()
            keys = set(re.findall(r'\{\{\s*T\.(\w+)', text)) if f.suffix == '.html' else set(re.findall(r'\bT\.(\w+)', text))
            if f.name == 'sw.js':
                continue
            missing |= {f'{f.name}:{k}' for k in keys if k not in TETUN}
        self.assertEqual(missing, set())

    def test_dynamic_error_keys_exist(self):
        # errText() dan login memakai T['err_' + kode]; kode ini dikembalikan server.
        for code in ('email_invalid', 'rate_limited', 'code_wrong', 'code_invalid', 'voucher_unknown', 'voucher_used',
                     'no_access', 'daily_limit', 'tutor_failed', 'refused', 'busy'):
            self.assertIn('err_' + code, TETUN)
        self.assertIn('mission_full', TETUN)  # mission.js memakai T.mission_full langsung

    def test_placeholders_are_known(self):
        for k, v in TETUN.items():
            self.assertLessEqual(set(re.findall(r'\{(\w+)\}', v)), {'n', 'email', 'date'}, k)
