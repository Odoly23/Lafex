import { $, T, api, errText, fmt } from './common.js';

const S = { id: null, left: 0, timer: null, submitting: false };
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

function tick() {
  S.left = Math.max(0, S.left - 1);
  $('timer').textContent = `${Math.floor(S.left / 60)}:${String(S.left % 60).padStart(2, '0')}`;
  if (S.left === 0) submit();
}

function render(questions) {
  $('qn').textContent = questions.length;
  $('qs').replaceChildren(...questions.map((q, i) => {
    const card = el('fieldset', 'card mb-3');
    const body = el('div', 'card-body');
    body.append(el('legend', 'h6', `${i + 1}. ${q.question}`));
    for (const [k, text] of Object.entries(q.choices)) {
      const id = `q${q.id}${k}`;
      const wrap = el('div', 'custom-control custom-radio mb-1');
      const input = el('input', 'custom-control-input');
      Object.assign(input, { type: 'radio', name: `q${q.id}`, id, value: k });
      input.addEventListener('change', () => { $('answered').textContent = document.querySelectorAll('#qs input:checked').length; });
      const label = el('label', 'custom-control-label', `${k.toUpperCase()}. ${text}`);
      label.htmlFor = id;
      wrap.append(input, label);
      body.append(wrap);
    }
    card.append(body);
    return card;
  }));
}

async function start() {
  $('msg').textContent = '';
  $('btn-start').disabled = true;
  try {
    const r = await api('/quiz/start/', {});
    S.id = r.attempt_id; S.left = r.seconds_left; S.submitting = false;
    render(r.questions);
    $('answered').textContent = '0';
    $('intro').hidden = true; $('result').hidden = true; $('quiz').hidden = false;
    clearInterval(S.timer); S.timer = setInterval(tick, 1000);
    tick();
  } catch (err) {
    $('msg').textContent = err.data?.error === 'quiz_none' ? T.quiz_none : errText({ message: err.data?.error || err.message });
    if (err.status === 401) location.href = '/login/';
  } finally { $('btn-start').disabled = false; }
}

async function submit() {
  if (S.submitting) return;
  S.submitting = true;
  clearInterval(S.timer);
  const answers = {};
  document.querySelectorAll('#qs input:checked').forEach((i) => { answers[i.name.slice(1)] = i.value; });
  try {
    const r = await api(`/quiz/${S.id}/submit/`, { answers });
    $('quiz').hidden = true; $('result').hidden = false;
    $('r-score').textContent = r.score; $('r-total').textContent = r.total;
    $('r-points').textContent = fmt(T.points_earned, { n: r.points });
    $('r-late').hidden = !r.late;
    $('review').replaceChildren(...r.review.map((x, i) => {
      const card = el('div', 'corr');
      card.append(el('strong', null, `${i + 1}. ${x.question}`));
      const line = el('div', null, `${x.ok ? '✔' : '✘'} ${x.given ? `${x.given.toUpperCase()}. ${x.choices[x.given]}` : '-'}`);
      line.style.color = x.ok ? '#2f5a2b' : '#b3541e';
      card.append(line);
      if (!x.ok) card.append(el('div', null, `${T.quiz_correct}: ${x.answer.toUpperCase()}. ${x.choices[x.answer]}`));
      if (x.explanation_tet) card.append(el('small', null, x.explanation_tet));
      return card;
    }));
    window.scrollTo(0, 0);
  } catch (err) {
    S.submitting = false;
    $('msg').textContent = errText({ message: err.data?.error || err.message });
  }
}

$('btn-start').onclick = start;
$('btn-again').onclick = start;
$('quiz').onsubmit = (e) => { e.preventDefault(); submit(); };
