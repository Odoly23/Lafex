import { $, T, api, fmt } from './common.js';

let email = '';
const msg = (t) => { $('msg').textContent = t || ''; };

async function sendCode() {
  msg('');
  try {
    await api('/auth/request/', { email });
    $('form-email').hidden = true;
    $('form-code').hidden = false;
    $('code-sent').textContent = fmt(T.code_sent, { email });
    $('code').focus();
  } catch (err) { msg(T['err_' + err.message] || T.err_generic); }
}

$('form-email').onsubmit = (e) => { e.preventDefault(); email = $('email').value.trim().toLowerCase(); sendCode(); };
$('btn-resend').onclick = sendCode;

$('form-code').onsubmit = async (e) => {
  e.preventDefault();
  msg('');
  try {
    await api('/auth/verify/', { email, code: $('code').value.trim() });
    location.href = '/';
  } catch (err) { msg(err.message === 'code_wrong' ? T.err_code_wrong : T['err_' + err.message] || T.err_generic); }
};
