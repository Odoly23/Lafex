// Fungsi bersama: API, teks Tetun, penyimpanan lokal, status maskot, service worker.
export const T = JSON.parse(document.getElementById('t-data').textContent);
export const $ = (id) => document.getElementById(id);
export const fmt = (s, vars = {}) => s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? '');

const cookie = (name) => document.cookie.split('; ').find((c) => c.startsWith(name + '='))?.split('=')[1];

export async function api(path, body) {
  const res = await fetch('/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: { 'content-type': 'application/json', 'X-CSRFToken': cookie('csrftoken') || '' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || 'error'), { status: res.status, data });
  return data;
}

export const errText = (err) => T['err_' + err.message] || T.err_generic;

// Maskot: idle | listening | thinking | speaking
export function mascot(state) {
  document.querySelectorAll('.mascot').forEach((m) => { m.className = 'mascot state-' + state; });
}

export async function logout() {
  // Bersihkan data di perangkat (IndexedDB + cache) agar tidak bocor ke pengguna berikutnya.
  try { indexedDB.deleteDatabase('lafex'); } catch { /* abaikan */ }
  try { for (const k of await caches.keys()) await caches.delete(k); } catch { /* abaikan */ }
  try { await api('/auth/logout/', {}); } catch { /* abaikan */ }
  location.href = '/login/';
}

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
}
