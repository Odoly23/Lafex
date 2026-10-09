// Service worker Lafex. Hanya cache berkas statis dan halaman /review/. API tidak pernah dicache.
const VERSION = 'lafex-{{ version }}';
const PRECACHE = [{% for u in urls %}'{{ u|escapejs }}'{% if not forloop.last %}, {% endif %}{% endfor %}];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin/')) return;

  if (url.pathname.startsWith('/static/')) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(VERSION).then((c) => c.put(req, copy));
      return res;
    })));
    return;
  }

  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          // Jangan simpan hasil redirect (mis. halaman login saat belum masuk) sebagai /review/.
          if (res.ok && !res.redirected && url.pathname === '/review/') {
            const copy = res.clone();
            caches.open(VERSION).then((c) => c.put('/review/', copy));
          }
          return res;
        })
        .catch(() => caches.match('/review/').then((hit) => hit || new Response(
          '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
          '<body style="font:18px system-ui;padding:24px"><h1>Lafex</h1><p>Offline. Konekta ba internet.</p>',
          { status: 503, headers: { 'content-type': 'text/html; charset=utf-8' } })))
    );
  }
});
