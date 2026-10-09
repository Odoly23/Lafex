// Sesi misi: Lafaek bicara (TTS) -> siswa bicara (STT) -> server/Claude -> ulang. Suara memakai Web Speech API.
import { $, T, api, mascot, errText } from './common.js';

const slug = $('mission').dataset.slug;
const EN = 'en-US';
const EXPLAIN_VOICE = 'pt-PT'; // Tetun belum punya suara di browser; Portugis paling dekat

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let voices = [];
const loadVoices = () => { voices = window.speechSynthesis ? speechSynthesis.getVoices() : []; };
if (window.speechSynthesis) { loadVoices(); speechSynthesis.onvoiceschanged = loadVoices; }
const pickVoice = (lang) =>
  voices.find((v) => v.lang.replace('_', '-').toLowerCase() === lang.toLowerCase()) ||
  voices.find((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase()));

const S = { id: null, last: null, busy: false, recog: null, gen: 0, done: false, placement: false };
const hint = (t) => { $('mic-hint').textContent = t; };
const msg = (t) => { $('msg').textContent = t || ''; };

function speak(text, lang) {
  return new Promise((resolve) => {
    if (!text || !window.speechSynthesis) return resolve();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    u.rate = $('chk-slow').checked ? 0.7 : 0.95;
    const v = pickVoice(lang);
    if (v) u.voice = v;
    u.onend = u.onerror = () => resolve();
    try { speechSynthesis.speak(u); } catch { resolve(); }
  });
}

function listen() {
  return new Promise((resolve, reject) => {
    const r = new SR();
    S.recog = r;
    r.lang = EN; r.interimResults = false; r.maxAlternatives = 1;
    let heard = '';
    r.onresult = (e) => { heard = e.results[0][0].transcript; };
    r.onerror = (e) => { if (e.error !== 'no-speech' && e.error !== 'aborted') reject(new Error(e.error)); };
    r.onend = () => { S.recog = null; resolve(heard); };
    r.start();
  });
}

const stopAll = () => {
  S.gen++;
  if (window.speechSynthesis) speechSynthesis.cancel();
  if (S.recog) { try { S.recog.abort(); } catch { /* abaikan */ } }
};

function bubble(role, text, extra) {
  const d = document.createElement('div');
  d.className = 'bubble ' + role;
  const p = document.createElement('div');
  p.textContent = text;
  d.append(p);
  if (extra) { const f = document.createElement('div'); f.className = 'fix'; f.textContent = extra; d.append(f); }
  $('chat').append(d);
  $('chat').scrollTop = $('chat').scrollHeight;
}

async function sayTurn(t, gen) {
  mascot('speaking'); hint(T.speaking);
  if (window.speechSynthesis && !pickVoice(EN)) $('voice-warn').textContent = T.no_voice;
  await speak(t.reply, EN);
  if (gen !== S.gen) return;
  if (t.correction) await speak(t.correction, EN);
  if (gen !== S.gen) return;
  await speak(t.explanation, EXPLAIN_VOICE);
  if (gen !== S.gen) return;
  mascot('idle'); hint(T.tap);
}

function showTurn(t) {
  S.last = t;
  bubble('tutor', t.reply, [t.correction && `${T.fix}: ${t.correction}`, t.explanation].filter(Boolean).join('\n'));
}

function fail(err) {
  S.busy = false; mascot('idle');
  const e = err.data?.error || err.message;
  hint(errText({ message: e }));
  if (err.status === 401) location.href = '/login/';
  if (e === 'mission_full') $('btn-finish').hidden = false;
  if (e === 'no_access') setTimeout(() => { location.href = '/'; }, 2500);
}

async function sendText(text) {
  if (S.busy || S.done) return;
  S.busy = true;
  bubble('user', text);
  mascot('thinking'); hint(T.thinking);
  const gen = ++S.gen;
  let r;
  try { r = await api(`/sessions/${S.id}/turn/`, { text }); } catch (err) { return fail(err); }
  showTurn(r.turn);
  $('btn-finish').hidden = false;
  S.done = r.done;
  await sayTurn(r.turn, gen);
  S.busy = false;
  if (r.done) {
    if (S.placement) return finish();
    hint(T.mission_full);
    $('btn-finish').scrollIntoView({ block: 'nearest' });
    $('btn-finish').focus();
    return;
  }
  if ($('chk-hands').checked && SR) cycle();
}

async function cycle() {
  const gen = S.gen;
  if (!SR) { hint(T.no_stt); $('text-input').focus(); return; }
  for (let miss = 0; miss < 2; miss++) {
    $('btn-mic').classList.add('on'); mascot('listening'); hint(T.listening);
    let heard = '';
    try { heard = await listen(); } catch { heard = ''; }
    $('btn-mic').classList.remove('on');
    if (gen !== S.gen) return;
    if (heard.trim()) return sendText(heard.trim());
    if (!$('chk-hands').checked) break;
  }
  mascot('idle'); hint(T.no_speech);
}

async function replay() {
  if (!S.last) return;
  stopAll();
  await sayTurn(S.last, S.gen);
}

async function finish() {
  stopAll();
  S.done = true;
  let r;
  try { r = await api(`/sessions/${S.id}/finish/`, {}); } catch (err) { return fail(err); }
  const s = r.summary;
  $('talk').hidden = true; $('result').hidden = false;
  mascot('idle');
  $('r-score').textContent = r.score;
  $('r-headline').textContent = s.headline;
  $('r-level').textContent = r.level;
  $('r-points').textContent = `${T.points}: ${r.points} · ${T.streak}: ${r.streak}`;
  if (r.new_certificate) { $('r-cert').href = `/sertifikat/${r.new_certificate}/`; $('r-cert').hidden = false; }
  const li = (txt) => { const e = document.createElement('li'); e.textContent = txt; return e; };
  $('r-tips').replaceChildren(...s.tips.map(li));
  $('r-vocab').replaceChildren(...s.vocab.map((v) => li(`${v.word} = ${v.meaning_tet}`)));
  $('r-corr').replaceChildren(...s.corrections.map((c) => {
    const d = document.createElement('div');
    d.className = 'corr';
    const a = document.createElement('s'); a.textContent = c.said;
    const b = document.createElement('div'); b.textContent = c.better;
    const w = document.createElement('small'); w.textContent = c.why_tet;
    d.append(a, b, w);
    return d;
  }));
  if (window.speechSynthesis) speak(s.headline, EXPLAIN_VOICE);
}

$('btn-start').onclick = async () => {
  msg('');
  $('btn-start').disabled = true;
  mascot('thinking');
  let r;
  try { r = await api('/sessions/', { mission: slug }); } catch (err) {
    $('btn-start').disabled = false; mascot('idle');
    msg(errText({ message: err.data?.error || err.message }));
    if (err.data?.error === 'no_access') setTimeout(() => { location.href = '/'; }, 2500);
    return;
  }
  S.id = r.session_id; S.placement = r.mission.is_placement;
  $('intro').hidden = true; $('talk').hidden = false;
  showTurn(r.turn);
  const gen = ++S.gen;
  await sayTurn(r.turn, gen);
  if ($('chk-hands').checked && SR) cycle();
};

$('btn-mic').onclick = () => {
  if (S.recog) { S.recog.stop(); return; }
  if (S.busy) { stopAll(); S.busy = false; mascot('idle'); hint(T.tap); return; }
  cycle();
};
$('btn-repeat').onclick = replay;
$('btn-finish').onclick = finish;
$('text-form').onsubmit = (e) => {
  e.preventDefault();
  const v = $('text-input').value.trim();
  if (!v) return;
  $('text-input').value = '';
  sendText(v);
};
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !$('talk').hidden && !['INPUT', 'BUTTON'].includes(document.activeElement.tagName)) {
    e.preventDefault(); $('btn-mic').click();
  }
});
window.addEventListener('pagehide', stopAll);
