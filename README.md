# Lafex

**Lafex = Lafaek Exploration.** Lafaek (buaya) adalah tutor AI yang berbicara langsung dengan siswa, memberi arahan dan koreksi sesuai level, untuk belajar bahasa Inggris lewat role-play (turis, imigrasi, toko, wawancara, dst.). Antarmuka, arahan, dan koreksi dalam **Tetun**.

Stack: **Django 6 + MySQL/MariaDB**, PWA (service worker + IndexedDB), Claude untuk tutor, suara lewat Web Speech API di browser (gratis).

## Status prototipe

| Ada | Belum |
|---|---|
| Daftar/masuk dengan email + kode 6 digit (tanpa PIN) | Pembayaran online (baru voucher) |
| Tes penempatan lewat suara -> level A1-C2 | Skenario Imigrasi, Toko, Wawancara (struktur sudah siap) |
| Skenario **Turis**: 6 misi di 3 band (pemula/menengah/lanjut) | Bahasa selain Inggris |
| Lafaek bicara & mendengar, mode tanpa tangan, koreksi dalam Tetun | Animasi mulut maskot (butuh gambar berlapis) |
| Paket gabungan (voucher sekali pakai) + batas harian | Verifikasi nomor HP (hanya email) |
| Review offline materi yang sudah dipelajari; terkunci saat paket habis | Audio rekaman untuk review |
| PWA bisa dipasang di layar utama | Panel analitik |

## Menjalankan

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt            # mysqlclient butuh libmariadb-dev + pkg-config

export SECRET_KEY=dev DEBUG=1              # SQLite untuk pengembangan cepat
python manage.py migrate
python manage.py seed_curriculum           # skenario & misi (aman diulang)
python manage.py create_vouchers 7d 5      # 5 voucher 7 hari
python manage.py runserver                 # http://localhost:8000
python manage.py test
```

Tanpa `ANTHROPIC_API_KEY` tutor berjalan dalam **mode demo** (skrip sederhana). Kode masuk email dicetak di konsol server selama `EMAIL_HOST` kosong.

MySQL/MariaDB: buat database `utf8mb4` lalu atur `DB_ENGINE=mysql` dan `DB_*` (lihat `.env.example`).

```sql
CREATE DATABASE lafex CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Produksi: `DEBUG=0`, `SECRET_KEY` acak, `python manage.py collectstatic`, jalankan dengan `gunicorn lafex.wsgi`, di belakang HTTPS (wajib untuk PWA, mikrofon, dan cookie aman).

## Struktur

| App | Isi |
|---|---|
| `accounts` | User berbasis email, kode login sekali pakai (di-hash, kedaluwarsa 10 menit, maks 5 tebakan, maks 5 permintaan/jam) |
| `billing` | Paket, voucher sekali pakai, masa aktif (voucher menumpuk), jatah giliran harian |
| `curriculum` | Skenario -> Misi (peran AI, tujuan, rubrik). Data awal di `curriculum/seed.py` |
| `tutor` | Sesi & giliran, mesin Claude (`ai.py`), penilaian akhir, review API |
| `frontend` | Halaman, teks Tetun (`strings.py`), JS, service worker, manifest |

Menambah skenario baru = menambah data di `curriculum/seed.py` (tanpa mengubah kode).

## Keputusan desain

- **AI percakapan wajib online.** Offline hanya untuk **review materi yang sudah dipelajari**: setelah misi selesai, hasilnya disimpan di IndexedDB. Review dikunci bila paket berakhir atau jam telepon dimundurkan. Ini perlindungan wajar, bukan DRM kedap.
- **Riwayat percakapan disimpan server**, bukan dikirim klien, supaya tidak bisa dipalsukan.
- **Jatah giliran dikembalikan** jika AI gagal (bukan salah siswa).
- Level hanya naik satu tingkat per misi (nilai >= 70); penempatan menetapkan level awal.
- Model default `claude-opus-5-5`; ganti dengan `TUTOR_MODEL`.
- Harga awal: 24 jam $1, 3 hari $2, 7 hari $3, 1 bulan $8, 1 tahun $60 (ubah lewat admin; migrasi `billing/0002_seed_plans.py` hanya mengisi nilai awal).

## Perlu ditinjau sebelum peluncuran

1. **Teks Tetun** (`frontend/strings.py`, judul/tujuan misi di `curriculum/seed.py`, email kode) ditulis sebaik mungkin dan **wajib dicek penutur asli**. Mintalah satu penutur menilai 30-50 koreksi Tetun pertama dari AI.
2. **Suara Tetun** belum ada di browser: penjelasan dibacakan dengan suara Portugis (`pt-PT`).
3. **Pengiriman email** butuh SMTP/layanan transaksional; periksa folder spam dan batas kirim.
4. **Suara Inggris di HP murah** bergantung pada perangkat; uji beberapa HP.
5. Jalur Claude diuji terhadap server palsu dan belum dengan kunci API sungguhan.
6. Aturan voucher/nilai tersimpan di Timor-Leste (Banco Central) perlu dicek sebelum dijual.
7. Maskot: tepi PNG masih punya sedikit garis putih tipis; sebaiknya dirapikan desainer atau dibuat versi vektor/berlapis.
