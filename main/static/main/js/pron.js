// Ujian pronunciation: Maun Lafaek membacakan contoh, siswa mengucapkan, skor dihitung server dari hasil rekonhesi suara.
import { $, T, api, errText, mascot } from './common.js';

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const S = { phrases: [], i: 0, scores: [], points: 0, rec: null };
const hint = (t) => { $('p-hint').textContent = t || ''; };

function speak(text) {
  return new Promise((resolve) => {
    if (!window.speechSynthesis || !text) return resolve();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'en-US'; u.rate = 0.85;
    u.onend = u.onerror = () => resolve();
    try { speechSynthesis.cancel(); speechSynthesis.speak(u); } catch { resolve(); }
  });
}

function listen() {
  return new Promise((resolve, reject) => {
    const r = new SR();
    S.rec = r;
    r.lang = 'en-US'; r.interimResults = false; r.maxAlternatives = 1;
    let out = { transcript: '', confidence: null };
    r.onresult = (e) => { const a = e.results[0][0]; out = { transcript: a.transcript, confidence: typeof a.confidence === 'number' ? a.confidence : null }; };
    r.onerror = (e) => { if (e.error !== 'no-speech' && e.error !== 'aborted') reject(new Error(e.error)); };
    r.onend = () => { S.rec = null; resolve(out); };
    r.start();
  });
}

function show() {
  const p = S.phrases[S.i];
  $('bar').style.width = `${(S.i / S.phrases.length) * 100}%`;
  $('p-text').textContent = p.text_en;
  $('p-tet').textContent = p.text_tet || '';
  $('p-result').hidden = true; hint(''); mascot('idle');
  $('btn-rec').disabled = false;
  speak(p.text_en);
}

async function record() {
  if (!SR) { hint(T.pron_no_stt); return; }
  if (S.rec) { S.rec.stop(); return; }
  const p = S.phrases[S.i];
  mascot('listening'); hint(T.listening);
  let heard = { transcript: '', confidence: null };
  try { heard = await listen(); } catch { /* dianggap tidak terdengar */ }
  mascot('thinking'); $('btn-rec').disabled = true;
  try {
    const r = await api('/pron/score/', { phrase_id: p.id, transcript: heard.transcript, confidence: heard.confidence });
    S.scores.push(r.score); S.points += r.points;
    $('p-score').textContent = r.score;
    $('p-words').replaceChildren(...r.detail.map((d) => {
      const s = document.createElement('span');
      s.className = `wd ${d.status}`;
      s.textContent = d.word;
      s.title = T['pron_' + d.status];
      return s;
    }));
    $('p-heard').textContent = r.heard || '-';
    $('p-result').hidden = false; hint('');
    $('btn-next').focus();
  } catch (err) {
    $('btn-rec').disabled = false;
    hint(errText({ message: err.data?.error || err.message }));
  }
  mascot('idle');
}

function next() {
  S.i++;
  if (S.i >= S.phrases.length) return finish();
  show();
}

function finish() {
  $('exam').hidden = true; $('final').hidden = false;
  const avg = Math.round(S.scores.reduce((a, b) => a + b, 0) / Math.max(1, S.scores.length));
  $('f-avg').textContent = avg;
  $('f-points').textContent = `${T.points}: +${S.points}`;
}

async function start() {
  $('msg').textContent = '';
  $('btn-start').disabled = true;
  try {
    const r = await api('/pron/start/', {});
    S.phrases = r.phrases; S.i = 0; S.scores = []; S.points = 0;
    $('intro').hidden = true; $('final').hidden = true; $('exam').hidden = false;
    if (!SR) hint(T.pron_no_stt);
    show();
  } catch (err) {
    $('msg').textContent = err.data?.error === 'pron_none' ? T.pron_none : errText({ message: err.data?.error || err.message });
    if (err.status === 401) location.href = '/login/';
  } finally { $('btn-start').disabled = false; }
}

$('btn-start').onclick = start;
$('btn-again').onclick = start;
$('btn-listen').onclick = () => speak(S.phrases[S.i].text_en);
$('btn-rec').onclick = record;
$('btn-next').onclick = next;
window.addEventListener('pagehide', () => { if (window.speechSynthesis) speechSynthesis.cancel(); });
