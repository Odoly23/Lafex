// Kartu vokabulario: tampil Tetun, ketuk untuk melihat Inggris (+ suara), tandai "hatene"/"seidauk".
import { $, T, api, errText } from './common.js';

const slug = $('study').dataset.slug;
const S = { queue: [], i: 0, known: 0, total: 0 };

function say(text) {
  if (!window.speechSynthesis || !text) return;
  try { const u = new SpeechSynthesisUtterance(text); u.lang = 'en-US'; u.rate = 0.85; speechSynthesis.cancel(); speechSynthesis.speak(u); } catch { /* abaikan */ }
}

function show() {
  const it = S.queue[S.i];
  $('bar').style.width = `${(S.i / S.queue.length) * 100}%`;
  $('c-tet').textContent = it.tet;
  $('c-en').textContent = it.en;
  $('c-ex').textContent = it.example_en;
  $('c-answer').hidden = true; $('grade').hidden = true; $('btn-show').hidden = false;
  $('btn-show').focus();
}

function reveal() {
  const it = S.queue[S.i];
  $('c-answer').hidden = false; $('grade').hidden = false; $('btn-show').hidden = true;
  say(it.en);
  $('btn-yes').focus();
}

async function grade(known) {
  const it = S.queue[S.i];
  try { await api('/vocab/known/', { item_id: it.id, known }); } catch (err) { $('msg').textContent = errText({ message: err.data?.error || err.message }); }
  if (known) S.known++;
  S.i++;
  if (S.i >= S.queue.length) return finish();
  show();
}

function finish() {
  $('card').hidden = true; $('done').hidden = false;
  $('bar').style.width = '100%';
  $('d-sum').textContent = `${S.known}/${S.queue.length} ${T.vocab_known}`;
}

async function load() {
  $('done').hidden = true;
  const data = await api(`/vocab/${slug}/`);
  // Kata yang belum dikuasai lebih dulu, diacak; maksimal 10 kartu per putaran.
  const shuffle = (a) => a.map((x) => [Math.random(), x]).sort((p, q) => p[0] - q[0]).map((x) => x[1]);
  S.queue = [...shuffle(data.items.filter((x) => !x.known)), ...shuffle(data.items.filter((x) => x.known))].slice(0, 10);
  S.i = 0; S.known = 0;
  if (!S.queue.length) { $('empty').hidden = false; $('card').hidden = true; return; }
  $('card').hidden = false;
  show();
}

$('btn-show').onclick = reveal;
$('btn-yes').onclick = () => grade(true);
$('btn-no').onclick = () => grade(false);
$('btn-say').onclick = () => say(S.queue[S.i].en);
$('btn-again').onclick = load;
load().catch((err) => { if (err.status === 401) location.href = '/login/'; else $('msg').textContent = errText({ message: err.data?.error || err.message }); });
