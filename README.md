# Tarombo

Pendataan dan pelestarian silsilah marga untuk Odoo 19.

Ringkasan
- Nama modul: Tarombo
- Versi: 19.0.1.0.0
- Deskripsi singkat: Platform pendataan, penelusuran, dan pelestarian silsilah marga (tarombo), mengikuti kaidah pencatatan tarombo asli.
- Author: Cv Sel Studio
- Website: https://selstudio.id
- Lisensi: LGPL-3

Fitur utama
- Manajemen pohon silsilah (pohon tarombo)
- Data orang, marga, wilayah, punguan
- Dashboard analitik (menggunakan eCharts)
- Geo picker dan peta (Leaflet)
- Wizard untuk pencatatan partuturan dan usulan
- Data awal (sample data) untuk marga, wilayah, punguan, dan usulan

Persyaratan
- Odoo 19
- Dependensi Odoo: base, mail, web
- Tidak ada paket Python spesifik selain yang disediakan Odoo core

Instalasi (singkat)
1. Salin folder `tarombo` ke direktori addons Odoo Anda (misal: addons path pada konfigurasi Odoo).
2. Restart server Odoo.
3. Perbarui daftar aplikasi di Apps > Update Apps List.
4. Cari modul "Tarombo" dan klik Install.

Instalasi via command-line (contoh pada environment Odoo)
- Restart Odoo lalu jalankan upgrade modul:
  - di shell Odoo: odoo -c /path/to/odoo.conf -d <db_name> -u tarombo

Struktur penting
- `models/` — model Python untuk entitas (pohon, orang, marga, dsb.)
- `views/` — XML views dan menu
- `data/` — data demo dan inisialisasi
- `static/` — aset frontend (echarts, leaflet, komponen JS/SCSS)
- `security/` — aturan akses

Remote GitHub dan branch
- Remote origin: https://github.com/rofianto507/tarombo.git
- Branch saat ini: master

Kontribusi
- Silakan buka issue atau pull request di repository GitHub.
- Ikuti konvensi kode Odoo dan sertakan deskripsi perubahan.

Lisensi
- Modul ini dilisensikan di bawah LGPL-3.

Kontak
- Author: Cv Sel Studio
- Email: (lihat metadata proyek atau hubungi maintainer repository)
