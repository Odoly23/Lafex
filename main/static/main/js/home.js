import { $, T, api, fmt, errText } from './common.js';

function renderMe(me) {
  $('h-streak').textContent = fmt(T.streak_days, { n: me.streak });
  $('h-points').textContent = me.points;
  $('h-level').textContent = me.level;
  $('access-line').textContent = me.free_mode ? T.free_mode
    : me.active ? fmt(T.access_active, { date: new Date(me.expires_at).toLocaleDateString() })
    : fmt(T.access_free, { n: me.turns_left });
  $('buy-card').hidden = me.free_mode;
}

// Dipasang sejak awal (bukan setelah data termuat) agar klik cepat tidak hilang.
$('btn-redeem').onclick = async () => {
  $('redeem-msg').textContent = '';
  try {
    renderMe(await api('/redeem/', { code: $('voucher').value }));
    $('voucher').value = '';
    $('redeem-msg').textContent = T.redeemed;
  } catch (err) { $('redeem-msg').textContent = errText(err); }
};

(async () => {
  try {
    const me = await api('/me/');
    renderMe(me);
    $('placement-cta').hidden = me.placement_done;
    $('plans').replaceChildren(...me.plans.map((p) => {
      const li = document.createElement('li');
      li.textContent = `${p.label}: $${p.price_usd}`;
      return li;
    }));
  } catch (err) {
    if (err.status === 401) location.href = '/login/';
  }
})();
