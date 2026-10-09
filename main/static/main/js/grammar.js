import { $, T, api, errText, fmt } from './common.js';

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

$('grammar-form').onsubmit = async (e) => {
  e.preventDefault();
  const text = $('gtext').value.trim();
  if (text.length < 2) return;
  $('gmsg').textContent = '';
  $('gbtn').disabled = true;
  $('gbtn').textContent = T.thinking;
  try {
    const r = await api('/grammar/', { text });
    $('gresult').hidden = false;
    $('g-ok').hidden = !r.ok;
    $('g-ok').textContent = r.ok ? T.grammar_ok : '';
    $('g-corrected').textContent = r.corrected;
    $('g-explanation').textContent = r.explanation;
    $('g-errors-box').hidden = r.errors.length === 0;
    $('g-errors').replaceChildren(...r.errors.map((x) => {
      const d = el('div', 'corr');
      d.append(el('s', null, x.wrong), el('div', null, x.right), el('small', null, x.why_tet));
      return d;
    }));
    $('g-points').textContent = fmt(T.grammar_points, { n: r.points });
    if (window.speechSynthesis && r.corrected) {
      try { const u = new SpeechSynthesisUtterance(r.corrected); u.lang = 'en-US'; speechSynthesis.cancel(); speechSynthesis.speak(u); } catch { /* abaikan */ }
    }
  } catch (err) {
    $('gmsg').textContent = errText({ message: err.data?.error || err.message });
    if (err.status === 401) location.href = '/login/';
  } finally {
    $('gbtn').disabled = false;
    $('gbtn').textContent = T.grammar_check;
  }
};
