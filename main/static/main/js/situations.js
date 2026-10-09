import { $, T, api } from './common.js';

const BANDS = ['beginner', 'intermediate', 'advanced'];

function render(data, me) {
  const root = $('scenarios');
  root.replaceChildren();
  for (const sc of data.scenarios) {
    const box = document.createElement('div');
    box.className = 'scenario mb-3';
    const h = document.createElement('h2');
    h.className = 'h5';
    h.textContent = `${sc.emoji} ${sc.title_tet}`;
    box.append(h);
    for (const band of BANDS) {
      for (const m of sc.missions.filter((x) => x.band === band)) {
        const a = document.createElement('a');
        a.className = 'mission-item' + (band === me.band ? ' rec' : '');
        a.href = `/mission/${m.slug}/`;
        a.textContent = m.title_tet;
        if (band === me.band) { const t = document.createElement('span'); t.className = 'tag'; t.textContent = T.recommended; a.append(t); }
        const small = document.createElement('small');
        small.textContent = `${T['band_' + band]}${m.best_score != null ? ` · ${T.best_score}: ${m.best_score}` : ''}`;
        a.append(small);
        box.append(a);
      }
    }
    root.append(box);
  }
}

(async () => {
  try {
    const [me, cur] = await Promise.all([api('/me/'), api('/curriculum/')]);
    render(cur, me);
  } catch (err) { if (err.status === 401) location.href = '/login/'; }
})();
