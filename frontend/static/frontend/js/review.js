// Review: online mengambil dari server dan menyimpan di IndexedDB; offline membaca dari IndexedDB.
// Terkunci bila paket sudah berakhir atau jam telepon dimundurkan.
import { $, T, api } from './common.js';

const CLOCK_SLACK_MS = 5 * 60 * 1000;

function db() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('lafex', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('kv');
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
const kv = {
  async get(k) { const d = await db(); return new Promise((r) => { const q = d.transaction('kv').objectStore('kv').get(k); q.onsuccess = () => r(q.result); q.onerror = () => r(undefined); }); },
  async set(k, v) { const d = await db(); return new Promise((r) => { const t = d.transaction('kv', 'readwrite'); t.objectStore('kv').put(v, k); t.oncomplete = () => r(); t.onerror = () => r(); }); },
  async del(k) { const d = await db(); return new Promise((r) => { const t = d.transaction('kv', 'readwrite'); t.objectStore('kv').delete(k); t.oncomplete = () => r(); t.onerror = () => r(); }); },
};

const note = (t) => { $('note').textContent = t || ''; };

function render(sessions) {
  const root = $('list');
  root.replaceChildren();
  if (!sessions.length) { note(T.review_empty); return; }
  for (const s of sessions) {
    const d = document.createElement('details');
    d.className = 'rv';
    const sum = document.createElement('summary');
    const title = document.createElement('span');
    title.textContent = s.mission.title_tet;
    const score = document.createElement('span');
    score.textContent = `${s.score}/100 · ${s.level}`;
    sum.append(title, score);
    d.append(sum);
    const date = document.createElement('small');
    date.textContent = new Date(s.finished_at).toLocaleString();
    d.append(date);
    for (const t of s.turns) {
      const p = document.createElement('p');
      p.textContent = `${t.role === 'user' ? T.you : T.tutor}: ${t.text}`;
      d.append(p);
      if (t.correction || t.explanation) {
        const f = document.createElement('p');
        f.className = 'fix';
        f.textContent = [t.correction && `${T.fix}: ${t.correction}`, t.explanation].filter(Boolean).join(' - ');
        d.append(f);
      }
    }
    const vocab = s.summary?.vocab || [];
    if (vocab.length) {
      const h = document.createElement('h2'); h.textContent = T.vocab;
      const ul = document.createElement('ul');
      for (const v of vocab) { const li = document.createElement('li'); li.textContent = `${v.word} = ${v.meaning_tet}`; ul.append(li); }
      d.append(h, ul);
    }
    root.append(d);
  }
}

async function showOffline() {
  const saved = await kv.get('review');
  if (!saved) { note(T.review_need_online); return; }
  const now = Date.now();
  const lastSeen = (await kv.get('last_seen')) || 0;
  if (now > Date.parse(saved.expires_at)) { note(T.review_locked); return; }
  if (now + CLOCK_SLACK_MS < lastSeen) { note(T.review_clock); return; } // jam dimundurkan
  await kv.set('last_seen', Math.max(lastSeen, now));
  note(T.review_offline);
  render(saved.sessions);
}

(async () => {
  note(T.loading);
  try {
    const data = await api('/review/');
    await kv.set('review', data);
    await kv.set('last_seen', Math.max((await kv.get('last_seen')) || 0, Date.parse(data.generated_at), Date.now()));
    note('');
    render(data.sessions);
    if (data.sessions.length) note(T.review_saved);
  } catch (err) {
    if (err.status === 401) { location.href = '/login/'; return; }
    if (err.status === 402) { await kv.del('review'); note(T.review_locked); return; }
    await showOffline(); // tanpa jaringan
  }
})();
