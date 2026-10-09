from odoo import http, fields
from odoo.http import request, Response

# Halaman publik (bukan menu backend) yang dibutuhkan untuk syarat publish di
# Google Play & Apple App Store: Kebijakan Privasi, Hapus Akun (Play Store
# mewajibkan jalur web selain jalur in-app), dan Dukungan (App Store Connect
# mewajibkan Support URL). Kontennya sengaja generik/universal (tidak
# menyebut istilah khas satu platform saja) supaya URL yang sama bisa dipakai
# untuk submission Android maupun iOS. Pola & struktur HTML meniru persis
# digital_kamtibmas/controllers/privacy_policy.py + account_deletion.py yang
# sudah pernah lolos review Play Store, isinya disesuaikan untuk Tarombo.

_KONTAK_EMAIL = 'dharukun@yahoo.com'
_PENGEMBANG = 'CV Mitra Hoki Maju Mapan'

_PRIVACY_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kebijakan Privasi – Tarombo</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F5F4F0;color:#16261B;line-height:1.7;font-size:15px}
.header{background:#2E5339;padding:36px 24px 32px;text-align:center}
.header-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(200,162,74,.18);border:1px solid rgba(200,162,74,.35);border-radius:20px;padding:4px 14px;margin-bottom:16px}
.header-badge span{color:#C8A24A;font-size:12px;font-weight:600;letter-spacing:.8px;text-transform:uppercase}
.header h1{color:#fff;font-size:clamp(22px,5vw,28px);font-weight:800;letter-spacing:-.3px;margin-bottom:6px}
.header-sub{color:rgba(255,255,255,.6);font-size:13px}
.header-divider{width:40px;height:3px;background:#C8A24A;border-radius:2px;margin:18px auto 0;opacity:.7}
.container{max-width:760px;margin:0 auto;padding:32px 20px 60px}
.intro{background:#fff;border-radius:12px;border:1px solid #E4E0D4;padding:20px 24px;margin-bottom:28px;border-left:4px solid #2E5339}
.intro p{color:#5B6B5F;font-size:14px}
.intro strong{color:#16261B}
.section{background:#fff;border:1px solid #E4E0D4;border-radius:12px;margin-bottom:16px;overflow:hidden}
.section-header{display:flex;align-items:center;gap:12px;padding:18px 20px;border-bottom:1px solid #E4E0D4}
.section-icon{width:36px;height:36px;border-radius:8px;background:rgba(46,83,57,.08);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.section-icon svg{width:18px;height:18px}
.section-title{font-size:15px;font-weight:700;color:#16261B}
.section-body{padding:18px 20px}
.section-body p{color:#5B6B5F;font-size:14px;margin-bottom:10px}
.section-body p:last-child{margin-bottom:0}
.item-list{list-style:none}
.item-list li{display:flex;gap:10px;color:#5B6B5F;font-size:14px;padding:6px 0;border-bottom:1px solid #EFEDE4}
.item-list li:last-child{border-bottom:none}
.item-list li::before{content:'';width:6px;height:6px;border-radius:50%;background:#C8A24A;margin-top:8px;flex-shrink:0}
.contact-box{background:#2E5339;border-radius:12px;padding:24px;margin-top:28px;text-align:center}
.contact-box h3{color:#fff;font-size:16px;font-weight:700;margin-bottom:10px}
.contact-box p{color:rgba(255,255,255,.65);font-size:13px;margin-bottom:4px}
.contact-box a{color:#C8A24A;text-decoration:none;font-weight:600}
.footer{text-align:center;padding:12px 24px 24px;color:#8A8578;font-size:12px}
</style>
</head>
<body>
<div class="header">
  <div class="header-badge"><span>Dokumen Resmi</span></div>
  <h1>Kebijakan Privasi</h1>
  <p class="header-sub">Tarombo &mdash; Silsilah Marga Silaen</p>
  <div class="header-divider"></div>
</div>
<div class="container">
  <div class="intro">
    <p><strong>Terakhir diperbarui: 4 Oktober 2026</strong><br>
    Kebijakan Privasi ini menjelaskan bagaimana aplikasi <strong>Tarombo</strong>
    yang dikembangkan dan dikelola oleh <strong>%(pengembang)s</strong> mengumpulkan,
    menggunakan, dan melindungi data pribadi pengguna. Dengan menggunakan aplikasi
    ini, Anda menyetujui ketentuan dalam kebijakan ini.</p>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
      </div>
      <div class="section-title">Data yang Kami Kumpulkan</div>
    </div>
    <div class="section-body">
      <p>Aplikasi ini mengumpulkan jenis data berikut:</p>
      <ul class="item-list">
        <li><strong>Data Akun</strong> &mdash; nama, alamat email/username, dan kata sandi (terenkripsi) saat mendaftar; atau nama, email, dan foto profil dari akun Google apabila Anda memilih masuk dengan Google.</li>
        <li><strong>Data Silsilah</strong> &mdash; nama, jenis kelamin, sundut, marga, punguan, urutan kelahiran, dan hubungan keluarga (ayah, anak, pernikahan) yang tercatat dalam pohon silsilah, termasuk data yang Anda usulkan melalui fitur Usulan.</li>
        <li><strong>Data Pribadi Anggota</strong> &mdash; tanggal lahir dan (bila berlaku) tanggal wafat, umur yang dihitung dari keduanya, status masih hidup atau telah wafat, serta alamat domisili (wilayah sampai tingkat desa dan alamat lengkap). Tanggal dapat berupa perkiraan: bila hanya tahun yang diketahui, dicatat sebagai 1 Januari tahun tersebut.</li>
        <li><strong>Riwayat Pendidikan &amp; Pekerjaan</strong> &mdash; jenjang, institusi, jurusan, jabatan, instansi, dan bidang pekerjaan, yang ditampilkan di Direktori Keahlian dan profil anggota.</li>
        <li><strong>Lampiran &amp; Arsip</strong> &mdash; foto dan dokumen yang Anda unggah melalui fitur Usulan atau Arsip.</li>
        <li><strong>Data Lokasi (opsional)</strong> &mdash; (a) koordinat GPS perangkat, HANYA apabila Anda secara eksplisit mengaktifkan "Bagikan Lokasi ke Kerabat"; dan (b) titik lokasi domisili yang Anda pilih di peta saat mengajukan usulan. Keduanya bersifat opsional dan dapat dihapus kapan saja.</li>
        <li><strong>Notifikasi Dalam Aplikasi</strong> &mdash; riwayat notifikasi status usulan dan klaim akun Anda, termasuk judul, isi, dan waktu notifikasi.</li>
        <li><strong>Token Notifikasi Perangkat</strong> &mdash; pengenal perangkat (token Firebase Cloud Messaging) yang dikirim ke server kami agar aplikasi dapat mengirim notifikasi, misalnya status usulan atau klaim akun Anda. Layanan pengiriman notifikasi disediakan oleh Google Firebase.</li>
      </ul>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      </div>
      <div class="section-title">Tujuan Penggunaan Data</div>
    </div>
    <div class="section-body">
      <ul class="item-list">
        <li>Menampilkan dan mengelola pohon silsilah keluarga (tarombo) marga Silaen.</li>
        <li>Memproses klaim identitas dan verifikasi keanggotaan oleh pengurus punguan.</li>
        <li>Memproses usulan penambahan atau koreksi data silsilah yang diajukan anggota.</li>
        <li>Menghitung hubungan kekerabatan (partuturan) antar anggota.</li>
        <li>Menampilkan direktori keahlian/profesi sesama anggota.</li>
        <li>Menampilkan peta kerabat terdekat, khusus untuk anggota yang memilih berbagi lokasi.</li>
        <li>Menampilkan umur dan informasi keluarga pada profil anggota.</li>
        <li>Mengirim notifikasi status usulan dan klaim akun Anda.</li>
      </ul>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      </div>
      <div class="section-title">Berbagi Data dengan Pihak Lain</div>
    </div>
    <div class="section-body">
      <p>Data yang dikumpulkan <strong>tidak dijual, disewakan, atau dibagikan</strong> kepada pihak komersial mana pun. Data hanya dapat diakses oleh:</p>
      <ul class="item-list">
        <li>Pengurus punguan/komunitas marga Silaen yang berwenang, untuk keperluan verifikasi keanggotaan dan pengelolaan data silsilah.</li>
        <li><strong>Sesama anggota</strong> yang sudah terverifikasi dapat melihat di dalam aplikasi: nama, sundut, marga, dan punguan; umur; alamat domisili termasuk alamat lengkap; riwayat pendidikan dan pekerjaan (Direktori Keahlian); serta titik lokasi hanya apabila pemilik data mengaktifkan berbagi lokasi. Tanggal lahir dan tanggal wafat yang persis, serta koordinat yang tidak dibagikan, <strong>tidak</strong> ditampilkan kepada anggota lain.</li>
        <li>Tim pengelola dari %(pengembang)s selaku pengembang aplikasi, terbatas untuk keperluan pemeliharaan sistem.</li>
      </ul>
      <p style="margin-top:12px">Pengiriman notifikasi push menggunakan layanan Google Firebase Cloud Messaging, yang memproses token perangkat Anda. Apabila Anda masuk menggunakan akun Google, proses autentikasi ditangani langsung oleh Google sesuai kebijakan privasi Google; kami hanya menerima nama, email, dan foto profil dasar setelah Anda memberikan izin.</p>
      <p>Pengungkapan data kepada pihak eksternal lain hanya dilakukan apabila diwajibkan oleh peraturan perundang-undangan yang berlaku di Indonesia.</p>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      </div>
      <div class="section-title">Keamanan Data</div>
    </div>
    <div class="section-body">
      <p>Data disimpan di server pengelola Tarombo dengan proteksi akses berbasis autentikasi dan hak akses berjenjang (anggota, pengurus, administrator). Transmisi data antara aplikasi dan server menggunakan protokol HTTPS yang terenkripsi.</p>
      <p>Meskipun kami menerapkan langkah-langkah keamanan yang wajar, tidak ada sistem yang sepenuhnya aman. Kami berkomitmen untuk menangani setiap insiden keamanan secara cepat dan bertanggung jawab.</p>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
      </div>
      <div class="section-title">Penyimpanan &amp; Retensi Data</div>
    </div>
    <div class="section-body">
      <p>Data silsilah bersifat historis dan disimpan sebagai arsip keluarga untuk tujuan pelestarian tarombo, sehingga umumnya disimpan dalam jangka panjang meski akun pengunggahnya sudah tidak aktif. Data akun pribadi (login, sesi) disimpan selama akun masih digunakan. Pengguna dapat mengajukan penghapusan akun melalui fitur Hapus Akun di aplikasi.</p>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      </div>
      <div class="section-title">Hak Pengguna</div>
    </div>
    <div class="section-body">
      <p>Pengguna berhak untuk:</p>
      <ul class="item-list">
        <li>Mengetahui data pribadi apa saja yang tersimpan dalam sistem.</li>
        <li>Mengajukan koreksi data silsilah melalui fitur Usulan, atau menghubungi pengurus punguan.</li>
        <li>Mencabut izin berbagi lokasi kapan saja melalui pengaturan aplikasi.</li>
        <li>Mengajukan penghapusan akun melalui fitur Hapus Akun di aplikasi atau halaman web ini.</li>
      </ul>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
      </div>
      <div class="section-title">Perubahan Kebijakan Privasi</div>
    </div>
    <div class="section-body">
      <p>Kebijakan ini dapat diperbarui sewaktu-waktu. Perubahan signifikan akan diinformasikan melalui notifikasi aplikasi atau pembaruan halaman ini. Tanggal "Terakhir diperbarui" di bagian atas halaman akan selalu mencerminkan versi terkini.</p>
    </div>
  </div>

  <div class="contact-box">
    <h3>Hubungi Kami</h3>
    <p>Pertanyaan seputar kebijakan privasi dapat disampaikan kepada:</p>
    <p style="margin-top:10px"><strong style="color:#fff">%(pengembang)s</strong></p>
    <p>Pengembang Aplikasi Tarombo</p>
    <p style="margin-top:8px"><a href="mailto:%(email)s">%(email)s</a></p>
  </div>
</div>
<div class="footer">&copy; 2026 Tarombo &mdash; %(pengembang)s. Seluruh hak dilindungi.</div>
</body>
</html>""".replace('%(pengembang)s', _PENGEMBANG).replace('%(email)s', _KONTAK_EMAIL)


_SUPPORT_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dukungan &amp; Bantuan – Tarombo</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F5F4F0;color:#16261B;line-height:1.7;font-size:15px}
.header{background:#2E5339;padding:36px 24px 32px;text-align:center}
.header-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(200,162,74,.18);border:1px solid rgba(200,162,74,.35);border-radius:20px;padding:4px 14px;margin-bottom:16px}
.header-badge span{color:#C8A24A;font-size:12px;font-weight:600;letter-spacing:.8px;text-transform:uppercase}
.header h1{color:#fff;font-size:clamp(22px,5vw,28px);font-weight:800;letter-spacing:-.3px;margin-bottom:6px}
.header-sub{color:rgba(255,255,255,.6);font-size:13px}
.header-divider{width:40px;height:3px;background:#C8A24A;border-radius:2px;margin:18px auto 0;opacity:.7}
.container{max-width:760px;margin:0 auto;padding:32px 20px 60px}
.intro{background:#fff;border-radius:12px;border:1px solid #E4E0D4;padding:20px 24px;margin-bottom:28px;border-left:4px solid #2E5339}
.intro p{color:#5B6B5F;font-size:14px}
.intro strong{color:#16261B}
.section{background:#fff;border:1px solid #E4E0D4;border-radius:12px;margin-bottom:16px;overflow:hidden}
.section-header{display:flex;align-items:center;gap:12px;padding:18px 20px;border-bottom:1px solid #E4E0D4}
.section-icon{width:36px;height:36px;border-radius:8px;background:rgba(46,83,57,.08);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.section-icon svg{width:18px;height:18px}
.section-title{font-size:15px;font-weight:700;color:#16261B}
.section-body{padding:18px 20px}
.faq-item{border-bottom:1px solid #EFEDE4;padding:14px 0}
.faq-item:last-child{border-bottom:none}
.faq-q{font-size:14px;font-weight:700;color:#16261B;margin-bottom:6px}
.faq-a{font-size:14px;color:#5B6B5F}
.contact-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
@media(max-width:480px){.contact-grid{grid-template-columns:1fr}}
.contact-card{background:#fff;border:1px solid #E4E0D4;border-radius:12px;padding:18px 20px;text-align:center}
.contact-card-icon{width:44px;height:44px;border-radius:50%;background:rgba(46,83,57,.08);display:flex;align-items:center;justify-content:center;margin:0 auto 12px}
.contact-card-icon svg{width:22px;height:22px}
.contact-card h4{font-size:14px;font-weight:700;color:#16261B;margin-bottom:4px}
.contact-card p{font-size:13px;color:#5B6B5F}
.contact-card a{color:#2E5339;text-decoration:none;font-weight:600}
.doc-links{display:flex;flex-direction:column;gap:10px;margin-top:4px}
.doc-link{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#F5F4F0;border:1px solid #E4E0D4;border-radius:8px;text-decoration:none;color:#2E5339;font-size:14px;font-weight:600}
.doc-link svg{width:16px;height:16px;flex-shrink:0}
.badge-hours{display:inline-block;background:rgba(46,83,57,.08);color:#2E5339;font-size:12px;font-weight:700;padding:2px 10px;border-radius:20px;margin-top:6px}
.footer{text-align:center;padding:12px 24px 24px;color:#8A8578;font-size:12px}
</style>
</head>
<body>
<div class="header">
  <div class="header-badge"><span>Pusat Bantuan</span></div>
  <h1>Dukungan &amp; Bantuan</h1>
  <p class="header-sub">Tarombo &mdash; Silsilah Marga Silaen</p>
  <div class="header-divider"></div>
</div>
<div class="container">
  <div class="intro">
    <p><strong>Kami siap membantu Anda.</strong><br>
    Temukan jawaban atas pertanyaan umum di bawah ini, atau hubungi tim kami
    langsung melalui email. Kami akan merespons setiap pertanyaan dalam waktu
    <strong>1 &times; 24 jam</strong> pada hari kerja.</p>
  </div>

  <div class="contact-grid">
    <div class="contact-card">
      <div class="contact-card-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
      </div>
      <h4>Email Dukungan</h4>
      <p><a href="mailto:%(email)s">%(email)s</a></p>
      <span class="badge-hours">Setiap hari, 08.00 &ndash; 20.00 WIB</span>
    </div>
    <div class="contact-card">
      <div class="contact-card-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      </div>
      <h4>Waktu Respons</h4>
      <p>Pertanyaan &amp; laporan direspons dalam</p>
      <span class="badge-hours">Maks. 1 &times; 24 jam</span>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      </div>
      <div class="section-title">Pertanyaan Umum (FAQ)</div>
    </div>
    <div class="section-body">
      <div class="faq-item">
        <div class="faq-q">Bagaimana cara mendaftar akun Tarombo?</div>
        <div class="faq-a">Buka aplikasi, pilih "Belum punya akun? Daftar" (atau masuk langsung dengan akun Google), lalu ikuti langkah pendaftaran. Setelah masuk, Anda akan diminta melengkapi klaim identitas.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">Apa itu "Klaim Identitas" dan kenapa wajib?</div>
        <div class="faq-a">Klaim identitas adalah proses menautkan akun Anda ke data diri Anda sendiri di pohon silsilah, atau mengajukan diri sebagai orang baru bila belum tercatat. Ini diperlukan agar data keluarga privat marga Silaen hanya dikelola oleh anggota yang identitasnya sudah diverifikasi pengurus. Anda tetap bisa menjelajahi sebagian fitur sebelum klaim disetujui.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">Klaim identitas saya berapa lama diproses?</div>
        <div class="faq-a">Klaim ditinjau langsung oleh pengurus punguan. Waktu peninjauan tergantung kesediaan pengurus; Anda akan melihat status "Menunggu Verifikasi" berubah otomatis di aplikasi begitu disetujui atau ditolak.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">Bagaimana cara mengusulkan koreksi atau tambahan data silsilah?</div>
        <div class="faq-a">Gunakan menu "Usulan" di aplikasi (tersedia setelah identitas Anda terverifikasi) untuk mengajukan penambahan data baru atau koreksi data yang sudah ada, lengkap dengan lampiran foto/dokumen pendukung.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">Lokasi saya di fitur "Kerabat Terdekat" siapa saja yang bisa lihat?</div>
        <div class="faq-a">Titik lokasi Anda hanya tampil di peta apabila Anda sendiri mengaktifkan "Bagikan Lokasi ke Kerabat". Fitur ini nonaktif secara default dan dapat dimatikan kapan saja dari aplikasi.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">Bagaimana cara menghapus akun saya?</div>
        <div class="faq-a">Buka menu Akun di dalam aplikasi, pilih "Hapus Akun", lalu ikuti langkah konfirmasi. Anda juga bisa mengajukan lewat formulir web di <a href="/hapus-akun">tarombo.selstudio.id/hapus-akun</a>. Permintaan diproses oleh administrator dalam maksimal 30 hari kerja.</div>
      </div>
      <div class="faq-item">
        <div class="faq-q">Apakah data saya aman?</div>
        <div class="faq-a">Ya. Seluruh transmisi data menggunakan protokol HTTPS yang terenkripsi, dan data tidak dijual atau dibagikan kepada pihak komersial mana pun. Baca Kebijakan Privasi kami untuk informasi lengkap.</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      </div>
      <div class="section-title">Dokumen Resmi</div>
    </div>
    <div class="section-body">
      <div class="doc-links">
        <a class="doc-link" href="/kebijakan-privasi">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          Kebijakan Privasi
        </a>
        <a class="doc-link" href="/hapus-akun">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
          Hapus Akun
        </a>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="section-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2E5339" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
      </div>
      <div class="section-title">Informasi Aplikasi</div>
    </div>
    <div class="section-body">
      <ul style="list-style:none">
        <li style="padding:4px 0;color:#5B6B5F;font-size:14px"><strong style="color:#16261B">Nama Aplikasi</strong>&nbsp;&mdash;&nbsp;Tarombo</li>
        <li style="padding:4px 0;color:#5B6B5F;font-size:14px"><strong style="color:#16261B">Pengembang</strong>&nbsp;&mdash;&nbsp;%(pengembang)s</li>
        <li style="padding:4px 0;color:#5B6B5F;font-size:14px"><strong style="color:#16261B">Platform</strong>&nbsp;&mdash;&nbsp;Android &amp; iOS</li>
        <li style="padding:4px 0;color:#5B6B5F;font-size:14px"><strong style="color:#16261B">Kontak Pengembang</strong>&nbsp;&mdash;&nbsp;%(email)s</li>
      </ul>
    </div>
  </div>
</div>
<div class="footer">&copy; 2026 Tarombo &mdash; %(pengembang)s. Seluruh hak dilindungi.</div>
</body>
</html>""".replace('%(pengembang)s', _PENGEMBANG).replace('%(email)s', _KONTAK_EMAIL)


_HAPUS_AKUN_FORM_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Permintaan Hapus Akun – Tarombo</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F5F4F0;color:#16261B;line-height:1.6;font-size:15px;min-height:100vh;display:flex;flex-direction:column}}
.header{{background:#2E5339;padding:28px 24px;text-align:center}}
.header h1{{color:#fff;font-size:20px;font-weight:800;margin-bottom:4px}}
.header p{{color:rgba(255,255,255,.6);font-size:13px}}
.container{{max-width:520px;margin:32px auto;padding:0 20px;flex:1}}
.card{{background:#fff;border-radius:12px;border:1px solid #E4E0D4;padding:28px 24px}}
.card h2{{font-size:16px;font-weight:700;margin-bottom:6px}}
.card .desc{{color:#5B6B5F;font-size:13px;margin-bottom:24px;line-height:1.6}}
label{{display:block;font-size:13px;font-weight:600;color:#16261B;margin-bottom:6px}}
input,textarea{{width:100%;padding:10px 12px;border:1px solid #E4E0D4;border-radius:8px;font-size:14px;color:#16261B;background:#fff;margin-bottom:16px;outline:none;font-family:inherit}}
input:focus,textarea:focus{{border-color:#2E5339;box-shadow:0 0 0 3px rgba(46,83,57,.12)}}
textarea{{resize:vertical;min-height:80px}}
.btn{{width:100%;background:#DC2626;color:#fff;border:none;border-radius:8px;padding:13px;font-size:15px;font-weight:700;cursor:pointer;margin-top:4px}}
.btn:hover{{background:#b91c1c}}
.alert{{padding:14px 16px;border-radius:8px;font-size:13px;margin-bottom:20px;display:none}}
.alert-success{{background:#dcfce7;color:#166534;border:1px solid #bbf7d0;display:block}}
.alert-error{{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;display:block}}
.note{{font-size:12px;color:#8A8578;text-align:center;margin-top:20px;line-height:1.6}}
.footer{{text-align:center;padding:20px;color:#8A8578;font-size:12px}}
</style>
</head>
<body>
<div class="header">
  <h1>Permintaan Hapus Akun</h1>
  <p>Tarombo &mdash; Silsilah Marga Silaen</p>
</div>
<div class="container">
  <div class="card">
    <h2>Formulir Permintaan</h2>
    <p class="desc">
      Isi formulir di bawah untuk mengajukan permintaan penghapusan akun Tarombo Anda.
      Permintaan akan diproses oleh administrator dalam <strong>maksimal 30 hari kerja</strong>.
      Cara yang sama juga tersedia langsung di dalam aplikasi, pada menu Akun &gt; Hapus Akun.
    </p>
    <div id="msg-success" class="alert alert-success" style="display:none">
      &#10003; Permintaan Anda telah diterima. Admin akan menghubungi Anda dan memproses dalam 30 hari kerja.
    </div>
    <div id="msg-error" class="alert alert-error" style="display:none">
      Terjadi kesalahan. Silakan coba lagi.
    </div>
    <form id="frm">
      <label for="nama">Nama Lengkap *</label>
      <input type="text" id="nama" name="nama" placeholder="Nama sesuai akun" required>
      <label for="login">Username / Email *</label>
      <input type="text" id="login" name="login" placeholder="Username atau email yang terdaftar" required>
      <label for="alasan">Alasan (opsional)</label>
      <textarea id="alasan" name="alasan" placeholder="Ceritakan alasan penghapusan akun Anda (opsional)"></textarea>
      <button type="submit" class="btn" id="btn-submit">Kirim Permintaan</button>
    </form>
    <p class="note">
      Dengan mengirim formulir ini, Anda memahami bahwa data akun dan tautan
      identitas Anda ke data silsilah akan dihapus secara permanen. Data
      silsilah keluarga itu sendiri tetap disimpan sebagai arsip bersama,
      sesuai tujuan pelestarian tarombo.
    </p>
  </div>
</div>
<div class="footer">&copy; 2026 Tarombo &mdash; {pengembang}</div>
<script>
document.getElementById('frm').addEventListener('submit', async function(e) {{
  e.preventDefault();
  const btn = document.getElementById('btn-submit');
  btn.disabled = true; btn.textContent = 'Mengirim...';
  document.getElementById('msg-success').style.display = 'none';
  document.getElementById('msg-error').style.display = 'none';
  try {{
    const res = await fetch('/hapus-akun/submit', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        jsonrpc: '2.0',
        method: 'call',
        params: {{
          nama:   document.getElementById('nama').value.trim(),
          login:  document.getElementById('login').value.trim(),
          alasan: document.getElementById('alasan').value.trim(),
        }}
      }})
    }});
    const data = await res.json();
    if (data.result && data.result.ok) {{
      document.getElementById('frm').style.display = 'none';
      document.getElementById('msg-success').style.display = 'block';
    }} else {{
      document.getElementById('msg-error').style.display = 'block';
      btn.disabled = false; btn.textContent = 'Kirim Permintaan';
    }}
  }} catch {{
    document.getElementById('msg-error').style.display = 'block';
    btn.disabled = false; btn.textContent = 'Kirim Permintaan';
  }}
}});
</script>
</body>
</html>""".format(pengembang=_PENGEMBANG)


_KESELAMATAN_ANAK_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Standar Keselamatan Anak – Tarombo</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F5F4F0;color:#16261B;line-height:1.7;font-size:15px}
.header{background:#2E5339;padding:32px 24px;text-align:center}
.header h1{color:#fff;font-size:clamp(21px,5vw,26px);font-weight:800;margin-bottom:6px}
.header p{color:rgba(255,255,255,.6);font-size:13px}
.container{max-width:760px;margin:0 auto;padding:28px 20px 50px}
.card{background:#fff;border:1px solid #E4E0D4;border-radius:12px;padding:20px 22px;margin-bottom:16px}
.card h2{font-size:16px;font-weight:700;margin-bottom:8px}
.card p,.card li{color:#5B6B5F;font-size:14px;margin-bottom:8px}
.card ul{padding-left:20px}
a{color:#2E5339;font-weight:600}
.footer{text-align:center;padding:12px 24px 24px;color:#8A8578;font-size:12px}
</style>
</head>
<body>
<div class="header">
  <h1>Standar Keselamatan Anak</h1>
  <p>Tarombo &mdash; Silsilah Marga Silaen</p>
</div>
<div class="container">
  <div class="card">
    <h2>Komitmen Kami</h2>
    <p><strong>%(pengembang)s</strong> melarang keras segala bentuk pelecehan dan eksploitasi seksual terhadap
    anak-anak (CSAE) serta materi pelecehan seksual terhadap anak (CSAM) di dalam aplikasi <strong>Tarombo</strong>.
    Materi semacam itu tidak diizinkan dalam bentuk apa pun, termasuk teks, foto, dokumen, audio, maupun video.</p>
  </div>
  <div class="card">
    <h2>Bagaimana Tarombo Dirancang</h2>
    <ul>
      <li>Aplikasi ditujukan bagi pengguna <strong>berusia 18 tahun ke atas</strong>.</li>
      <li>Tarombo adalah aplikasi silsilah komunitas tertutup. <strong>Tidak ada</strong> fitur pesan pribadi, obrolan,
      kolom komentar, atau unggahan publik antarpengguna, dan tidak ada fitur untuk berkenalan atau bertemu dengan orang asing.</li>
      <li>Akses data silsilah hanya untuk anggota yang identitasnya <strong>diverifikasi pengurus</strong> (klaim akun).</li>
      <li>Foto dan dokumen yang diusulkan anggota <strong>ditinjau pengurus</strong> sebelum data diperbarui; arsip keluarga
      hanya diunggah oleh pengurus.</li>
      <li>Lokasi bersifat opsional dan hanya dibagikan bila pengguna sendiri mengaktifkannya.</li>
    </ul>
  </div>
  <div class="card">
    <h2>Tindakan terhadap Pelanggaran</h2>
    <p>Pengurus dapat menolak usulan, menghapus konten, dan menonaktifkan akun yang melanggar. Konten yang
    terindikasi CSAM akan segera dihapus dan dilaporkan kepada pihak berwenang serta organisasi yang berwenang
    menangani CSAM sesuai hukum yang berlaku.</p>
  </div>
  <div class="card">
    <h2>Melaporkan Masalah</h2>
    <p>Bila Anda menemukan konten atau perilaku yang mengkhawatirkan terkait keselamatan anak, segera hubungi kami di
    <a href="mailto:%(email)s">%(email)s</a>. Kontak ini ditangani oleh pengelola aplikasi yang siap
    menjelaskan praktik pencegahan CSAM serta kepatuhan terhadap kebijakan ini.</p>
    <p>Lihat juga <a href="/kebijakan-privasi">Kebijakan Privasi</a> dan <a href="/dukungan">Dukungan</a>.</p>
  </div>
</div>
<div class="footer">&copy; 2026 Tarombo &mdash; %(pengembang)s</div>
</body>
</html>""".replace('%(pengembang)s', _PENGEMBANG).replace('%(email)s', _KONTAK_EMAIL)


class TaromboPublicPagesController(http.Controller):

    @http.route('/standar-keselamatan-anak', type='http', auth='public', website=False, csrf=False)
    def keselamatan_anak(self, **kwargs):
        return Response(_KESELAMATAN_ANAK_HTML, content_type='text/html; charset=utf-8')

    @http.route('/kebijakan-privasi', type='http', auth='public', website=False, csrf=False)
    def privacy_policy(self, **kwargs):
        return Response(_PRIVACY_HTML, content_type='text/html; charset=utf-8')

    @http.route('/dukungan', type='http', auth='public', website=False, csrf=False)
    def support(self, **kwargs):
        return Response(_SUPPORT_HTML, content_type='text/html; charset=utf-8')

    # ── Hapus akun: jalur web (publik, tanpa login) ─────────────────────────────
    @http.route('/hapus-akun', type='http', auth='public', website=False, csrf=False)
    def hapus_akun_form(self, **kwargs):
        return Response(_HAPUS_AKUN_FORM_HTML, content_type='text/html; charset=utf-8')

    @http.route('/hapus-akun/submit', type='json', auth='public', csrf=False)
    def hapus_akun_submit(self, nama='', login='', alasan='', **kwargs):
        if not nama or not login:
            return {'ok': False, 'error': 'Data tidak lengkap'}
        user = request.env['res.users'].sudo().search([('login', '=', login.strip())], limit=1)
        request.env['tarombo.hapus_akun_request'].sudo().create({
            'nama': nama.strip(),
            'login': login.strip(),
            'alasan': alasan.strip() or False,
            'user_id': user.id if user else False,
            'tanggal_request': fields.Datetime.now(),
        })
        return {'ok': True}
