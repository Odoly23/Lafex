# Lafex

**Lafex = Lafaek Exploration.** **Maun Lafaek** (si buaya) adalah tutor AI bahasa Inggris untuk masyarakat Timor-Leste: siswa berbicara atau menulis, Maun Lafaek menjawab, mengoreksi, dan menyesuaikan level (A1-C2). Antarmuka, arahan, dan koreksi dalam **Tetun**.

Stack: **Django 6 + MySQL/MariaDB + Django REST Framework**, PWA (service worker + IndexedDB), Claude untuk tutor, suara lewat Web Speech API di browser (gratis). Semua library front-end disimpan **lokal** (tanpa CDN).

## Menu

**Siswa (HP / web)**

| Menu | Isi |
|---|---|
| **Uma** (Beranda) | Sapaan Maun Lafaek, streak harian, pontu, nível, kartu ke semua fitur |
| **Aprende** | Ngobrol bebas (chat + suara dengan AI), Situasaun (role-play: turis, hotel, restoran...), Vokabulario Tetun -> Inglés (eskola, merkadu, kantór), Grammar fix, Revisaun (offline) |
| **Treinu** | Avaliasaun Quiz (10 soal, dinilai di server), Ezame pronunciation (5 kalimat) |
| **Perfíl** | Nível, pontu, streak, **munisipiu**, sertifikadu (bisa dicetak; ada kode verifikasi publik), isi nama |

**Admin / Guru**

| Menu | Isi | Peran |
|---|---|---|
| **Painel** | Estudante ativu ohin, total chat, sesaun, pakote ativu, vaucher, grafik, dan **peta Highcharts estudante per munisipiu** | staff, admin |
| **Master data** | Jere estudante (nama/nível/aktif; admin: beri paket), Materia no vokabulario (misaun, kategoria + vokabulario, import massal), Pergunta quiz (CRUD + import) | staff, admin |
| **Monitorizasaun** | Chat estudante ho Maun Lafaek (dengan log audit), pontu pronunciation ki'ik liu (siswa yang perlu dibantu) | staff, admin |
| **Konfigurasaun** | Instruksi tambahan untuk Maun Lafaek (prompt), mode **gratis / pakai paket**, batas harian, harga paket, **batch vaucher cetak** | admin |

Dari menu **Modu estudante**, staff/admin bisa mencoba semua halaman siswa.

## Menjalankan

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt            # mysqlclient butuh libmariadb-dev + pkg-config

export SECRET_KEY=dev DEBUG=1              # SQLite untuk pengembangan cepat
python manage.py migrate
python manage.py seed_all                  # misi, vokabulario, soal quiz, kalimat pronunciation (aman diulang)
python manage.py createsuperuser           # akun admin (otomatis masuk grup admin)
python manage.py create_vouchers 7d 5      # atau lewat /staff/vaucher/
python manage.py runserver                 # http://localhost:8000
python manage.py test
```

Tanpa `ANTHROPIC_API_KEY` tutor berjalan dalam **mode demo** (skrip sederhana). Kode masuk email dicetak di konsol server selama `EMAIL_HOST` kosong. Konfigurasi lengkap: `.env.example`.

MySQL/MariaDB: buat database `utf8mb4` lalu atur `DB_ENGINE=mysql` dan `DB_*`.

```sql
CREATE DATABASE lafex CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Produksi: `DEBUG=0`, `SECRET_KEY` acak, `python manage.py collectstatic`, `gunicorn lafex.wsgi`, di belakang HTTPS (wajib untuk PWA, mikrofon, dan cookie aman).

## Struktur

Gaya proyek Django Anda: satu app per domain, templat di `<app>/templates/<app>/`, view berbentuk fungsi untuk halaman dan `APIView` (DRF) untuk API, indentasi tab, peran lewat Django Groups, `verbose_name` Tetun di semua model.

```
lafex/        settings, urls (handler 403/404/500)
config/       decorators, api (APIAll/APIStaff/APIAdmin), auth, forms (Bootstrap), SystemSetting + halaman Konfigurasaun
users/        User berbasis email, kode login, edit estudante
billing/      paket, voucher, masa aktif, jatah harian, mode gratis
curriculum/   Skenario -> Misi (seed.py), edit misaun, hub materi
tutor/        sesi & giliran, ai.py (Claude), Grammar fix, review, views/ (api.py, pages.py)
vocab/        vokabulario Tetun -> Inglés (belajar + master + import)
quiz/         soal & percobaan quiz 5 menit (belajar + master + import)
pronounce/    kalimat & percobaan pronunciation, scoring.py
progress/     Activity (poin, streak), Sertifikat, Perfíl
custom/       Municipality (code, name, hckey Highcharts) + seed 13 munisipiu
report/       API grafik {label, obj}, Painel, Monitorizasaun (+ MonitorLog)
main/         layout/navbar/sidebar, templates/home/, static/main/ (css, js, library lokal), service worker, strings.py (teks Tetun)
```

**Tampilan:** Bootstrap 4 + jQuery + Font Awesome 4 + DataTables + Chart.js lokal (lihat `main/static/main/LICENSES.txt`). Topbar + navbar + sidebar HP yang mendorong isi halaman. Warna dari logo Lafaek (`app.css`). Tes menjaga agar tidak ada sumber eksternal.

**Peran (Groups):** `estudante` (otomatis untuk pengguna baru), `staff` (guru), `admin`. Halaman: `@login_required` + `@allowed_users(...)`. API: `APIView` dengan `SessionAuth401` (tanpa BasicAuthentication) + permission peran; galat seragam `{"error": kode}`; 401 bila belum masuk, 403 bila peran tidak cocok.

## Login

- **Kode email** (tanpa PIN) dan **Google / Facebook** (django-allauth, hanya login sosial: tidak ada pendaftaran/kata sandi lokal). **Daftar otomatis**: login pertama dengan cara apa pun langsung membuat akun siswa.
- Tombol Google/Facebook hanya muncul bila `GOOGLE_CLIENT_ID/SECRET` atau `FACEBOOK_APP_ID/SECRET` diisi. Daftarkan redirect URI `https://DOMAIN/accounts/google/login/callback/` dan `https://DOMAIN/accounts/facebook/login/callback/`. Facebook: aplikasi harus berstatus *Live* dan izin `email` aktif.
- Akun yang sudah ada digabung otomatis hanya bila penyedia menyatakan email **terverifikasi** (Google ya). Email Facebook dianggap tidak terverifikasi, jadi tidak pernah digabung otomatis ke akun yang ada (mencegah pengambilalihan akun).
- Tautan `?next=` hanya menerima jalur lokal (tanpa open redirect).

## Vaucher (gaya pulsa / token)

- Admin membuat **batch** per toko (`Konfigurasaun > Vaucher`): paket, jumlah (<= 500), label toko, masa berlaku. Sistem membuka halaman **cetak** (kartu A4 dengan kode, nomor seri, QR, petunjuk Tetun) dan tombol CSV.
- Kode 12 karakter acak (60 bit, tanpa huruf mudah tertukar). **Database hanya menyimpan hash** (HMAC); kode hanya tampil **sekali** di halaman cetak, jadi kebocoran database tidak membocorkan kode.
- **Sekali pakai**: setelah ditukar tidak valid lagi. Bisa **dikansela** per kartu atau per batch (kartu yang sudah dipakai tidak terpengaruh), punya **tanggal kedaluwarsa**, dan percobaan salah **dibatasi** (5 per siswa dan 30 per IP per 15 menit).
- QR membuka `/?kode=XXXX-XXXX-XXXX`: setelah login, kolom kode terisi (siswa tetap menekan tombol sendiri).
- Daftar batch menampilkan total, terpakai, sisa, dikansela, dan nilai yang terpakai (USD).

## Munisipiu dan peta

- `custom.Municipality` (code, name, **hckey**) diisi 13 munisipiu dengan `hckey` yang cocok dengan peta Highcharts `countries/tl/tl-all` (ada tes yang menjamin kecocokannya). Siswa memilih munisipiu di Perfíl (beranda mengajak yang belum memilih). Painel menggambar peta lewat `joinBy: 'hc-key'` dari database, plus ranking dan jumlah siswa tanpa munisipiu.

## Cara kerja fitur

- **Poin & streak:** setiap kegiatan tercatat di `Activity`. Streak = hari berturut-turut (zona waktu Dili); putus bila kemarin tidak belajar. Aturan poin satu tempat: `progress/services.py`. Poin vokabulario hanya sekali per kata; poin pronunciation hanya percobaan pertama per kalimat per hari.
- **Sertifikat:** terbit otomatis saat nível naik lewat situasaun (skor >= 70), mulai A2. Level dari tes penempatan dan ngobrol bebas **tidak** menerbitkan sertifikat. Halaman `/sertifikat/<kode>/` publik untuk verifikasi (hanya nama, nível, tanggal; tanpa email).
- **Quiz:** jawaban benar tidak dikirim ke browser; dinilai di server; batas 5 menit + toleransi 20 detik; terlambat = nilai dihitung tapi tanpa poin.
- **Mode gratis:** admin mematikan "Presiza pakote" -> semua siswa mendapat akses penuh dan batas harian "ho pakote"; review offline tetap berlaku 7 hari sejak terakhir online.
- **Prompt Maun Lafaek:** teks admin **ditambahkan** ke prompt dasar (maks 2000 karakter); format JSON dan aturan keselamatan tidak bisa diubah. Perubahan berlaku dalam <= 30 detik (cache per proses).
- **Offline:** AI percakapan wajib online. Offline hanya Revisaun (materi yang sudah dipelajari): disimpan di IndexedDB, terkunci bila paket berakhir atau jam HP dimundurkan.
- Grafik dihitung di Python (bukan fungsi tanggal MySQL) karena MySQL/MariaDB sering belum memuat tabel zona waktu.

## Batas yang jujur, dan hal yang perlu ditinjau

1. **Skor pronunciation adalah estimasi.** Sistem tidak mendengarkan rekaman: ia membandingkan kata yang berhasil dikenali pengenal suara di HP siswa dengan kalimat target (plus tingkat keyakinan pengenal). Cukup untuk latihan dan menandai siswa yang perlu dibantu, **bukan** penilaian fonem seperti penilai profesional. Penilaian sungguhan butuh layanan khusus (mis. Azure Pronunciation Assessment).
2. **Privasi chat.** Guru/admin bisa membaca chat siswa. Setiap pembukaan dicatat (`MonitorLog`) dan siswa diberi tahu di Perfíl. Putuskan kebijakan siapa yang boleh melihat, dan sampaikan ke siswa/orang tua (terutama anak-anak) sebelum peluncuran.
3. **Teks Tetun** (`main/strings.py`, `verbose_name`, judul misi, penjelasan quiz, vokabulario di `vocab/seed.py`) ditulis sebaik mungkin dan **wajib ditinjau penutur asli**. Mintalah satu penutur menilai 30-50 koreksi Tetun pertama dari AI.
4. **Suara Tetun** belum ada di browser: penjelasan dibacakan dengan suara Portugis (`pt-PT`).
5. **Pengiriman email** butuh SMTP/layanan transaksional. Verifikasi nomor HP (OTP) belum ada.
6. **Suara Inggris di HP murah** bergantung pada perangkat; pengenalan suara terbaik di Chrome/Edge (Android/desktop).
7. Jalur Claude diuji terhadap server palsu dan **belum dengan kunci API sungguhan**.
8. Pembayaran online belum ada (voucher saja). Cek aturan voucher/nilai tersimpan di Timor-Leste (Banco Central) sebelum dijual.
9. **Lisensi Highcharts.** Highmaps dan data petanya **bukan open source**: gratis hanya untuk penggunaan non-komersial (CC BY-NC; nirlaba, pribadi, pendidikan). Karena Lafex menjual paket, **lisensi Highmaps komersial harus dibeli** (https://shop.highsoft.com/highmaps). Kode peta terisolasi di fungsi `drawMunicipalities` (`report/static/report/js/dash.js`) agar mudah diganti bila perlu.
10. **Login Google/Facebook belum diuji dengan penyedia sungguhan** (butuh client id dari Anda); alurnya diuji dengan penyedia palsu, termasuk penolakan pengambilalihan akun.
11. **Vaucher:** `VOUCHER_PEPPER`/`SECRET_KEY` tidak boleh berubah setelah vaucher dicetak. Batas percobaan per IP memakai `REMOTE_ADDR`; di belakang proxy, atur proxy agar IP asli diteruskan. Kartu cetak sebaiknya hanya diaktifkan saat dijual jika toko rawan pencurian (fitur aktivasi per kartu belum ada).
12. Maskot: tepi PNG punya garis putih tipis; animasi mulut butuh gambar berlapis. Skenario Imigrasi, Toko, Wawancara belum diisi (strukturnya siap; cukup tambah data di `curriculum/seed.py` atau lewat halaman Misaun).
