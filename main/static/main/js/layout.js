// Sidebar HP (mendorong isi halaman), ingat keadaan terakhir. Klasik (bukan modul) agar jalan sebelum modul lain.
(function () {
  var ham = document.getElementById('btn-ham');
  var sb = document.getElementById('sidebar');
  if (!ham || !sb) return;
  function set(open) {
    sb.classList.toggle('active', open);
    document.body.classList.toggle('sb-open', open);
    ham.setAttribute('aria-expanded', open ? 'true' : 'false');
    try { sessionStorage.setItem('lafex.sb', open ? '1' : '0'); } catch (e) { /* abaikan */ }
  }
  ham.addEventListener('click', function () { set(!sb.classList.contains('active')); });
  window.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
  // Layar lebar tidak memakai sidebar: pastikan tidak ada margin yang tertinggal.
  window.matchMedia('(min-width: 992px)').addEventListener('change', function (m) { if (m.matches) set(false); });
})();
