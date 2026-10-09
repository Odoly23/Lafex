import { $, T, api } from './common.js';

(async () => {
  try {
    const { categories } = await api('/vocab/');
    $('cats').replaceChildren(...categories.map((c) => {
      const a = document.createElement('a');
      a.className = 'mission-item';
      a.href = `/belajar/kosakata/${c.slug}/`;
      a.textContent = `${c.emoji} ${c.name_tet}  /  ${c.name_en}`;
      const small = document.createElement('small');
      small.textContent = `${c.known}/${c.total} ${T.vocab_known}`;
      a.append(small);
      return a;
    }));
  } catch (err) { if (err.status === 401) location.href = '/login/'; }
})();
