// Painel staff: ambil data dari API (bentuk {label, obj}) lalu gambar dengan Chart.js (lokal).
import { $ } from '../../main/js/common.js';

const GREEN = '#3f6f3a', GREEN_LT = '#9cc58f', YELLOW = '#fed755', INK = '#2e3131';
const getJSON = (u) => fetch(u, { credentials: 'same-origin' }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
const common = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };

function chart(id, type, data, opts = {}) {
  return new Chart($(id), { type, data, options: { ...common, ...opts } });
}

(async () => {
  try {
    const s = await getJSON('/api/report/stats/');
    for (const k of ['aktif_ohin', 'total_chat', 'siswa', 'sesaun', 'pakote_ativu', 'vaucher_livre']) $('st-' + k).textContent = s[k];

    const daily = await getJSON('/api/report/sesaun-daily/');
    chart('ch-daily', 'line', { labels: daily.label, datasets: [{ data: daily.obj, borderColor: GREEN, backgroundColor: GREEN_LT, fill: true, tension: .3 }] },
      { scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } });

    const lv = await getJSON('/api/report/levels/');
    chart('ch-levels', 'bar', { labels: lv.label, datasets: [{ data: lv.obj, backgroundColor: GREEN }] },
      { scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } });

    const ms = await getJSON('/api/report/misaun/');
    // Nilai rata-rata (0-100); jumlah sesi ditulis di label supaya skala tidak bercampur.
    chart('ch-missions', 'bar', { labels: ms.label.map((l, i) => `${l} (${ms.obj[i]})`), datasets: [
      { label: 'Pontu média', data: ms.avg, backgroundColor: YELLOW, borderColor: INK, borderWidth: 1 },
    ] }, { scales: { y: { beginAtZero: true, max: 100 } } });

    const v = await getJSON('/api/report/vaucher/');
    chart('ch-vouchers', 'doughnut', { labels: v.label, datasets: [{ data: v.obj, backgroundColor: [GREEN, YELLOW], borderColor: '#fff' }] },
      { plugins: { legend: { display: true, position: 'bottom' } } });
  } catch (e) {
    if (String(e.message) === '401') location.href = '/login/';
  }
})();
