import { $, T, api } from './common.js';

function renderCerts(list) {
  const root = $('certs');
  root.replaceChildren();
  if (!list.length) { const p = document.createElement('p'); p.className = 'note'; p.textContent = T.profile_no_certs; root.append(p); return; }
  for (const c of list) {
    const a = document.createElement('a');
    a.className = 'mission-item';
    a.href = `/sertifikat/${c.code}/`;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = `${T.cert_title} ${c.level}`;
    const small = document.createElement('small');
    small.textContent = `${new Date(c.issued_at).toLocaleDateString()} · ${c.code} · ${T.profile_view_cert}`;
    a.append(small);
    root.append(a);
  }
}

(async () => {
  try {
    const p = await api('/profile/');
    $('p-level').textContent = p.level;
    $('p-points').textContent = p.points;
    $('p-streak').textContent = p.streak;
    $('p-best').textContent = p.best_streak;
    $('p-email').textContent = p.email;
    $('name').value = p.name;
    const { municipalities } = await api('/municipalities/');
    $('municipality').append(...municipalities.map((m) => new Option(m.name, m.id)));
    $('municipality').value = p.municipality ?? '';
    renderCerts(p.certificates);
  } catch (err) { if (err.status === 401) location.href = '/login/'; }
})();

$('form-name').onsubmit = async (e) => {
  e.preventDefault();
  $('name-msg').textContent = '';
  try {
    await api('/profile/', { name: $('name').value, municipality: $('municipality').value || null });
    $('name-msg').textContent = T.profile_saved;
  } catch { $('name-msg').textContent = T.err_generic; }
};
