import { $, T, api, fmt, logout, errText } from './common.js';

const BANDS = ['beginner', 'intermediate', 'advanced'];

function renderAccess(me) {
  $('access-line').textContent = me.active
    ? fmt(T.access_active, { date: new Date(me.expires_at).toLocaleDateString() })
    : fmt(T.access_free, { n: me.turns_left });
  $('level').textContent = me.level;
  $('status').textContent = me.email;
}

function renderScenarios(data, me) {
  const root = $('scenarios');
  root.replaceChildren();
  for (const sc of data.scenarios) {
    const box = document.createElement('div');
    box.className = 'scenario';
    const h = document.createElement('h3');
    h.textContent = `${sc.emoji} ${sc.title_tet}`;
    box.append(h);
    for (const band of BANDS) {
      for (const m of sc.missions.filter((x) => x.band === band)) {
        const a = document.createElement('a');
        a.className = 'mission' + (band === me.band ? ' rec' : '');
        a.href = `/mission/${m.slug}/`;
        a.textContent = m.title_tet;
        const tag = document.createElement('span');
        if (band === me.band) { tag.className = 'tag'; tag.textContent = T.recommended; a.append(tag); }
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
    renderAccess(me);
    renderScenarios(cur, me);
    $('placement-cta').hidden = me.placement_done;
    $('plans').replaceChildren(...me.plans.map((p) => {
      const li = document.createElement('li');
      li.textContent = `${p.label}: $${p.price_usd}`;
      return li;
    }));
    $('btn-redeem').onclick = async () => {
      $('redeem-msg').textContent = '';
      try {
        renderAccess(await api('/redeem/', { code: $('voucher').value }));
        $('voucher').value = '';
        $('redeem-msg').textContent = T.redeemed;
      } catch (err) { $('redeem-msg').textContent = errText(err); }
    };
  } catch (err) {
    if (err.status === 401) location.href = '/login/';
  }
})();
$('btn-logout').onclick = logout;
