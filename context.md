# Context: Modul Tarombo (Odoo 19)

> File ini adalah resume analisis kondisi modul saat ini. Gunakan sebagai acuan konteks
> setiap kali memulai sesi kerja baru pada project ini, agar tidak perlu membaca ulang
> seluruh source code dari nol.

Terakhir diperbarui: 2026-08-19 untuk bagian 1-8 (11 model + wizard + OWL pohon
silsilah + laporan). Bagian 9 (progres impor data real) ditambahkan 2026-09-07 —
bagian 1-8 **belum** disinkronkan dengan perubahan sesudah 08-19 (mis. Dashboard,
field wilayah di Usulan, penghapusan view hierarchy, dll — lihat riwayat percakapan
kalau perlu detailnya, belum dirangkum di sini).

## 1. Apa itu modul ini

**Tarombo** adalah platform pendataan, penelusuran, dan pelestarian **silsilah marga**
(tarombo = istilah adat Batak untuk catatan silsilah keturunan/marga). Filosofi desain
yang eksplisit dinyatakan di deskripsi manifest:

> "Modul ini dirancang mengikuti kaidah pencatatan tarombo, bukan menyesuaikan tarombo
> pada aplikasi silsilah umum."

Modul ini sudah berkembang jauh dari sekadar "daftar orang" menjadi sistem lengkap:
pohon silsilah patrilineal (sundut, cabang, partuturan/sapaan kekerabatan, visualisasi
OWL+ECharts), hierarki marga & wilayah administratif, data punguan (paguyuban lokal),
riwayat pernikahan (termasuk poligami, dengan peringatan adat semarga/padan), riwayat
pendidikan/pekerjaan, arsip media per orang, alur usulan perubahan data (draft →
diajukan → disetujui/ditolak), dan laporan "Direktori Keahlian" yang ditujukan dipakai
rutin oleh anggota biasa (bukan cuma pengurus/admin).

- **Developer/Author**: Cv Sel Studio (selstudio.id)
- **Kategori Odoo**: Tarombo (kategori custom sendiri)
- **Versi**: 19.0.1.0.0 — dibangun untuk **Odoo 19.0**
- **Status**: `application: True`, `installable: True`
- **License**: LGPL-3

## 2. Dependency

```python
'depends': ['base', 'mail', 'web', 'web_hierarchy']
```

- `base`, `mail` — standar.
- `web` — kebutuhan UI umum + asset bundle `web.assets_backend` (dipakai komponen OWL).
- `web_hierarchy` — **wajib** untuk view `<hierarchy>` pada `tarombo.orang`. Terpisah
  dari `web` inti; tanpa ini arch `<hierarchy>` gagal load (JS view type tak terdaftar).

## 3. Struktur File

```
tarombo/
├── __manifest__.py           # data list + assets (web.assets_backend)
├── __init__.py                # import models, wizard, hooks.post_init_hook
├── hooks.py                   # post_init_hook: isi ir.config_parameter leluhur_acuan_id
│                               #   dari orang bernama persis "Tuan Sihubil" bila ada
├── models/
│   ├── __init__.py
│   ├── tarombo_orang.py       # model inti: individu + pohon + domisili + riwayat + arsip
│   ├── tarombo_marga.py       # hierarki marga (_parent_store) + satu_keturunan/terikat_padan
│   ├── tarombo_padan.py       # sumpah persaudaraan leluhur antar-marga tak sekerabat
│   ├── tarombo_wilayah.py     # hierarki wilayah admin provinsi..desa (_parent_store)
│   ├── tarombo_punguan.py     # paguyuban/komunitas lokal
│   ├── tarombo_pernikahan.py  # riwayat pernikahan (poligami) + peringatan_adat
│   ├── tarombo_partuturan.py  # _inherit tarombo.orang — mesin sapaan kekerabatan
│   ├── tarombo_riwayat.py     # tarombo.pendidikan + tarombo.pekerjaan
│   ├── tarombo_usulan.py      # alur usulan perubahan data (workflow + sequence)
│   ├── tarombo_arsip.py       # media/dokumen per orang (foto/dokumen/audio/video/naskah)
│   └── tarombo_pohon.py       # _inherit tarombo.orang — get_pohon_data() utk OWL
├── wizard/
│   ├── __init__.py
│   ├── tarombo_partuturan_wizard.py       # TransientModel: hitung partuturan 2 orang
│   └── tarombo_partuturan_wizard_views.xml
├── static/
│   ├── description/icon.png
│   ├── lib/echarts/echarts.min.js         # ECharts di-vendor lokal, BUKAN CDN
│   └── src/components/pohon/              # komponen OWL pohon silsilah
│       ├── pohon.js    # ir.actions.client "tarombo_pohon_silsilah", pakai `echarts` global
│       ├── pohon.xml   # template tarombo.PohonSilsilah (pakai <Layout>)
│       └── pohon.scss
├── security/
│   ├── tarombo_security.xml         # category + privilege + 3 group berjenjang
│   ├── ir.model.access.csv          # access per model x per group
│   └── tarombo_usulan_security.xml  # ir.rule usulan (anggota: punya sendiri; pengurus: semua)
├── views/
│   ├── tarombo_orang_views.xml       # list, form (6 tab), hierarchy, search, action
│   ├── tarombo_marga_views.xml
│   ├── tarombo_padan_views.xml
│   ├── tarombo_wilayah_views.xml
│   ├── tarombo_punguan_views.xml
│   ├── tarombo_direktori_keahlian_views.xml  # laporan read-only untuk anggota
│   ├── tarombo_usulan_views.xml      # list (decoration), form (statusbar), kanban (per state)
│   ├── tarombo_arsip_views.xml       # kanban (pratinjau gambar), form, search
│   ├── tarombo_pohon_views.xml       # ir.actions.client action_tarombo_pohon_silsilah
│   └── menu.xml                       # seluruh menuitem modul
├── data/
│   ├── tarombo_marga_data.xml    # Tampubolon > Baringbing, Silaen (noupdate=1)
│   ├── tarombo_wilayah_data.xml  # Sumut > Kab. Toba/Asahan > Silaen/Kisaran Barat
│   ├── tarombo_punguan_data.xml  # "Punguan Pusat (Kurator Leluhur)" — utk leluhur historis
│   └── tarombo_usulan_data.xml   # ir.sequence USUL/%(year)s/0001
├── tests/
│   ├── __init__.py
│   └── test_partuturan.py    # 13 test: pohon uji + 10 kategori hubungan + simetri
└── static/description/icon.png
```

Belum ada demo data untuk `tarombo.padan` (marga contoh Tampubolon/Silaen/Baringbing
tidak match pasangan padan yang diketahui — perlu diisi manual sesuai marga nyata).

## 4. Model Data

### `tarombo.orang` ([models/tarombo_orang.py](models/tarombo_orang.py)) — model inti

Satu orang/individu dalam tarombo. `_inherit = ['mail.thread', 'mail.activity.mixin']`,
`_parent_name = 'ayah_id'`, `_parent_store = True`, `_order = 'sundut, urutan, name'`.

**Identitas**: `name`, `teknonim`, `jenis_kelamin` (L/P), `foto`, `marga_id`,
`punguan_id` (required), `partner_id`, `catatan`.
- `marga_id` **TIDAK** `required=True` di level field — leluhur puncak tanpa `ayah_id`
  (mis. Tuan Sihubil) sah tidak bermarga (mendahului percabangan marga). Wajib hanya
  kalau `ayah_id` terisi, lewat `@api.constrains` `_cek_marga_wajib`. View: field diberi
  `required="ayah_id"` (kondisional, bukan statis) supaya tanda wajib di UI ikut benar.
- `punguan_id` tetap `required=True` untuk semua orang termasuk leluhur historis — untuk
  kasus itu diisi record kurator/administratif (lihat `tarombo.punguan` di bawah), bukan
  klaim keanggotaan asli.
- **Konsekuensi ke `tarombo.usulan`**: `action_setujui()` untuk jenis "tambah" mewarisi
  `marga_id` dari `ayah_id.marga_id` — kalau `ayah_id` marga-less (mis. anak Tuan
  Sihubil), pewarisan ini gagal (`_cek_marga_wajib` akan menolak). Belum ada
  `usul_marga_id` di form usulan untuk menutup celah ini.

**Struktur pohon** (patrilineal murni — lihat bagian "partuturan" di bawah):
- `ayah_id` — Many2one biasa ke `tarombo.orang` (BUKAN related lewat pernikahan).
- `parent_path`, `anak_ids` (One2many via `ayah_id`).
- `sundut` (compute+store) — relatif terhadap leluhur acuan
  (`ir.config_parameter['tarombo.leluhur_acuan_id']`), bukan akar pohon absolut.
- `urutan` ("Anak ke-", required, default 1), **unik** per `ayah_id` (`_urutan_unik`).
- `urutan_putra` ("Putra ke-", compute+store) — peringkat hanya di antara saudara laki-laki.
- `jumlah_saudara` (compute+store) — saudara kandung, tidak termasuk diri sendiri.

**Keabsahan**: `status` (sahih/rumpang, default sahih), `sumber_ket`, `lengkap`
(compute+store = `status=='sahih' and bool(sumber_ket)`).

**Khusus perempuan**: `suami_nama`, `suami_marga_id`.

**Data pribadi**: `tahun_lahir`, `tahun_wafat` — `groups='tarombo.group_tarombo_pengurus'`.
`masih_hidup` — **TIDAK** dibatasi groups (lihat bagian 5).

**Pernikahan** (poligami): `pernikahan_ids`, `pernikahan_id` ("Dari istri ke-", domain
`suami_id = ayah_id`), `ibu_marga_id`/`ibu_nama` (related, store), `punya_istri_ganda`
(compute, toggle tampilan anak-per-istri di form).

**Domisili**: `provinsi_id` → `desa_id` (domain `=?`), `wilayah_id` (compute+store),
`negara_id` (default `base.id`), `alamat_catatan`. Sensitif (**groups=pengurus**):
`alamat_jalan`, `kode_pos`, `latitude`, `longitude`. `izin_lokasi` (TIDAK dibatasi
groups) — koordinat perorangan tampak di form hanya kalau `izin_lokasi=True` **dan**
pembacanya pengurus (gerbang di lapisan tampilan, bukan akses data/RPC).

**Riwayat**: `pendidikan_ids`/`pekerjaan_ids`, `pendidikan_tertinggi` (compute+store),
`pekerjaan_kini` + `bidang_kini` (satu compute method).

**Arsip**: `arsip_ids` (One2many ke `tarombo.arsip` via `orang_id`) — tab "Arsip" di form.

Constraint: `_cek_garis_perempuan`, `_cek_siklus` (`_has_cycle()`), `_cek_marga_wajib`,
`_cek_pernikahan`, `_cek_wilayah_domisili`.

### `tarombo.partuturan` ([models/tarombo_partuturan.py](models/tarombo_partuturan.py))

`_inherit = 'tarombo.orang'` — method `leluhur_bersama()` dan `hitung_partuturan()`
(sapaan kekerabatan: amang/anak, ompung/pahompu, haha/anggi, angkang/anggi, ito,
amangtua/amanguda, namboru/bere — cabang lebih tua dari `urutan`, bukan tahun lahir).
Hanya dongan tubu (patrilineal); hula-hula/garis ibu belum bisa dihitung.

### `tarombo.marga` ([models/tarombo_marga.py](models/tarombo_marga.py))

Hierarki marga berjenjang. `name`, `kode` (unik), `marga_induk_id`, `kelompok`
(toba/karo/simalungun/mandailing/angkola/pakpak), `keterangan`, `anak_ids`,
`complete_name` (compute+store+recursive), `jumlah_anggota` (compute via `child_of`).
- `satu_keturunan(self, lain)` — **diperbaiki**: awalnya cuma cek relasi leluhur-langsung
  (prefix `parent_path`), sekarang cek **akar marga yang sama** (elemen pertama
  `parent_path`) — jadi dua cabang berbeda dari marga akar yang sama (mis. Silaen &
  Baringbing, sama-sama anak Tampubolon) juga terdeteksi sebagai satu garis/dongan tubu,
  bukan cuma saat salah satunya leluhur langsung yang lain.
- `terikat_padan(self, lain)` — cek apakah dua marga (beda akar) sama-sama anggota
  satu record `tarombo.padan`.
- Constraint anti-siklus via `_has_cycle()`.

### `tarombo.padan` ([models/tarombo_padan.py](models/tarombo_padan.py))

Mencatat **sumpah persaudaraan leluhur** antar-marga yang **berbeda dan tidak
sekerabat secara hierarki** (mis. Hutabarat–Silaban, Manullang–Panjaitan, atau
kelompok besar seperti "Pomparan Parna" yang mengikat 60+ marga) — larangan menikah
adat Batak yang tidak bisa dideteksi dari pohon `marga_induk_id`. `name`, `marga_ids`
(Many2many), `keterangan`. Menu: Konfigurasi > Padan (admin-only). Belum ada seed data.

### `tarombo.wilayah` ([models/tarombo_wilayah.py](models/tarombo_wilayah.py))

Satu model berjenjang provinsi→kabupaten/kota→kecamatan→desa. `kode` (Kemendagri),
`name`, `tingkat` ('1'-'4'), `induk_id`, `parent_path`, `kode_pos`, `latitude`/
`longitude` (koordinat pusat wilayah — basis peta aman untuk anggota), `complete_name`.

### `tarombo.punguan` ([models/tarombo_punguan.py](models/tarombo_punguan.py))

Komunitas/paguyuban lokal — tidak menentukan penomoran sundut. `name`, `kode` (unik),
`keterangan`, `wilayah_id`, `pengurus_ids`, `aktif`, `jumlah_anggota` (compute).
**Sudah ada 1 seed record**: `data/tarombo_punguan_data.xml` → "Punguan Pusat (Kurator
Leluhur)" — dipakai untuk leluhur historis yang bukan anggota organisasi modern mana
pun (`punguan_id` tetap wajib di semua `tarombo.orang`).

### `tarombo.pernikahan` ([models/tarombo_pernikahan.py](models/tarombo_pernikahan.py))

`suami_id` (required, ondelete cascade, harus `jenis_kelamin='L'`), `urutan` ("Istri
ke-", unik per suami), `istri_nama`, `istri_marga_id` (required), `tahun`, `anak_ids`
(One2many `tarombo.orang` via `pernikahan_id`). `display_name`: `"Istri ke-2: Tiodora
br Sitorus"`.
- **`istri_orang_id` (Many2one penaut ke `tarombo.orang`, untuk kasus istri juga
  tercatat sendiri lintas punguan) SUDAH DIHAPUS** — dievaluasi tidak ada satu pun
  fitur yang membacanya, dan bikin bingung user (picker sempat tidak difilter). Kalau
  fitur hula-hula/garis-ibu dikerjakan nanti, field ini layak ditambahkan lagi — kali
  ini idealnya langsung dikasih `@api.onchange` yang auto-isi `istri_nama`/
  `istri_marga_id`, bukan cuma placeholder pasif.
- `peringatan_adat` (Char, compute, **tidak** disimpan) — bandingkan `istri_marga_id`
  vs `suami_id.marga_id` lewat `satu_keturunan()`/`terikat_padan()`. **Peringatan
  saja, TIDAK memblokir save** (keputusan eksplisit: sistem ini merekam silsilah apa
  adanya, termasuk kasus adat kontroversial, bukan jadi "polisi adat"). Tampil sebagai
  kolom di list Pernikahan pada form Anggota, baris ber-`decoration-danger` kalau ada
  peringatan.

### `tarombo.pendidikan` & `tarombo.pekerjaan` ([models/tarombo_riwayat.py](models/tarombo_riwayat.py))

Riwayat pendidikan (jenjang sd..s3+lain, institusi, jurusan, wilayah, tahun masuk/
lulus, status lulus) dan pekerjaan (jabatan, instansi, bidang, wilayah, tahun mulai/
selesai, status berjalan). Basis `pendidikan_tertinggi`/`pekerjaan_kini`/`bidang_kini`
pada `tarombo.orang` dan laporan Direktori Keahlian.

### `tarombo.usulan` ([models/tarombo_usulan.py](models/tarombo_usulan.py))

Alur usulan perubahan data — **tabel utama `tarombo.orang` cuma berisi data sahih**,
usulan diverifikasi dulu sebelum masuk. `_inherit = ['mail.thread', 'mail.activity.mixin']`.
- `name` diisi otomatis dari `ir.sequence` `tarombo.usulan` (`USUL/%(year)s/0001`).
- `jenis`: tambah/koreksi/lengkapi. `state`: draft→diajukan→disetujui/ditolak (tracking).
- Sasaran: `orang_id` (koreksi/lengkapi) atau `ayah_id`+`pernikahan_id` (tambah).
- Muatan `usul_*` dipetakan ke field `tarombo.orang` lewat `USUL_MUATAN_MAP` (method
  `_muatan()`) — hanya kolom yang benar-benar diisi. `usul_kota_id` dipetakan ke
  `kabupaten_id` (bukan `wilayah_id` yang compute+store, supaya bisa ditulis langsung).
- `action_ajukan()` / `action_setujui()` (create/write `tarombo.orang`, catat
  `orang_hasil_id`, `message_post` **ke chatter orang itu sendiri** — bukan cuma ke
  tabel usulan yang bisa diarsipkan/dihapus) / `action_tolak()` (wajib `alasan_tolak`,
  set `active=False`).
- Constraint: ayah harus laki-laki, `usul_urutan` tidak boleh bentrok dengan saudara
  (pesan menjelaskan nomor urut menentukan haha/anggi).
- **Security** (lihat `tarombo_usulan_security.xml`): dua `ir.rule` untuk
  `group_tarombo_anggota` (read+create milik sendiri; write hanya kalau `state=draft`
  DAN milik sendiri, dua rule terpisah karena satu `ir.rule` cuma berlaku untuk operasi
  yang `perm_*`-nya True) **plus** satu `ir.rule` `[(1,'=',1)]` untuk
  `group_tarombo_pengurus` yang meng-OR-kan diri ke rule anggota (pengurus/admin
  otomatis juga anggota lewat `implied_ids`, jadi tanpa rule override ini mereka akan
  ikut kena batasan "punya sendiri").
- View: list `decoration-*` per state, form `statusbar`+tombol (Setujui/Tolak
  `groups=pengurus`), kanban `default_group_by="state"`. Filter "Ditolak" di search
  eksplisit `active in [True, False]` karena `action_tolak` mengarsipkan record.

### `tarombo.arsip` ([models/tarombo_arsip.py](models/tarombo_arsip.py))

Media/dokumen per orang. `name`, `jenis` (foto/dokumen/audio/video/naskah), `orang_id`
(opsional), `punguan_id` (required), `tahun_perkiraan` (Char, bukan Integer — banyak
berkas lama cuma diketahui kisarannya), `sumber`, `keterangan`, `attachment_id`
(required), `pratinjau` (Image, compute dari `attachment_id.datas` **hanya** kalau
mimetype `image/*`, TIDAK `store` supaya tidak menduplikasi data biner attachment),
`publik` (default True — **baru sekadar disimpan, belum ada `ir.rule` yang benar-benar
menyaring arsip non-publik dari anggota**, access masih model-wide read-only).
Kanban dengan `pratinjau` sebagai tampilan utama (pola modern: `<field widget="image"
invisible="...">` langsung di `<t t-name="card">`, bukan helper `kanban_image()` lama).
Menu: Anggota > Arsip.

## 5. Visualisasi Pohon Silsilah (OWL + ECharts)

- **Backend**: `tarombo_pohon.py` (`_inherit tarombo.orang`), method `@api.model
  get_pohon_data(orang_id, mode)`. Return dict node `{id, name, teknonim, sundut,
  jenis_kelamin, status, selected, collapsed, has_more, children}` — **hanya data
  semantik mentah**, pemetaan ke bentuk/warna ECharts dilakukan di JS (bukan
  hardcode di Python).
  - Mode `cabang`: akar = ayah orang tsb (kalau ada); anak-anaknya = saudara dengan
    `collapsed=True` (kecuali cabang orang terpilih, di-expand penuh).
  - Mode `radial`: akar = leluhur acuan (fallback ke orang itu sendiri bila belum
    diatur); simpul fokus tetap ditandai `selected`.
  - Dibatasi `POHON_KEDALAMAN_MAKS=4` generasi / `POHON_SIMPUL_MAKS=200` simpul
    per panggilan (jaga performa).
- **Frontend**: `static/src/components/pohon/` — `ir.actions.client` bertag
  `tarombo_pohon_silsilah`, terdaftar via `registry.category("actions").add(...)`.
  Dipicu tombol "Pohon Silsilah" di header form `tarombo.orang` (`type="action"`,
  `name="%(action_tarombo_pohon_silsilah)d"` — **action XML wajib load sebelum**
  `tarombo_orang_views.xml` di manifest karena referensi `%(...)d`).
- **ECharts di-vendor lokal** (`static/lib/echarts/echarts.min.js`), **BUKAN CDN** —
  file disalin dari modul lain di server ini (`digital_kamtibmas`, `hr_smartatt`, dll
  sudah pakai file identik). Dimuat sebagai asset biasa di `web.assets_backend`
  (urutan sebelum `pohon.js`), lalu dipakai sebagai variabel **global** `echarts` di
  JS — **jangan** `import` (bukan modul ES). Pola ini terbukti jalan di produksi di
  modul lain server ini.
- Simbol: `circle` (L) / `diamond` (P). Warna beda sahih/rumpang; simpul terpilih
  `borderWidth` tebal. Klik simpul `collapsed` → fokus ulang tampilan ke orang itu
  (panggil ulang `get_pohon_data` dengan `orang_id` baru); klik simpul lain → buka
  form (`actionService.doAction` act_window).
- Dipilih opsi "tombol di form" (bukan view type baru) — jauh lebih sederhana,
  tidak perlu tulis `ArchParser`/`Renderer` custom seperti `<hierarchy>`.

## 6. Security

- **Privilege pattern Odoo 19**: `res.groups` tidak punya `category_id` langsung —
  lewat `res.groups.privilege` (`category_id` ada di situ), lalu `privilege_id`
  menunjuknya. 1 privilege (`privilege_tarombo_access`).
- **Group bertingkat** (`implied_ids`): `group_tarombo_anggota` → `group_tarombo_pengurus`
  → `group_tarombo_admin`. `base.user_admin` otomatis masuk admin saat install.
- **PENTING — bug nyata**: `group_tarombo_anggota` awalnya tidak implies
  `base.group_user` (Internal User) → user non-superuser dengan grup Tarombo saja
  tidak melihat menu backend sama sekali, walau access rights benar (`res.users.share`
  dihitung dari `all_group_ids` yang butuh `base.group_user` di closure-nya).
  **Sudah diperbaiki** (pola sama dipakai `fleet`, `digital_kamtibmas`).
- **`masih_hidup` sengaja TIDAK di-`groups=`** (beda dari `tahun_lahir`/`tahun_wafat`).
  Awalnya dibatasi pengurus, tapi itu bikin domain filter Direktori Keahlian error
  `AccessError` untuk anggota — field yang dibatasi `groups=` tetap dicek di level SQL
  compile (`_check_field_access` via `_field_to_sql`), bukan cuma tampilan. Pelajaran:
  field yang dipakai di **domain action/filter untuk grup lebih rendah** tidak boleh
  dibatasi `groups=`.
- **Record rule (`ir.rule`)**: baru ada untuk `tarombo.usulan` (lihat bagian 4). Model
  lain masih model-wide access saja (tidak ada pembatasan per marga/punguan/kepemilikan).
- **Access rights** pola konsisten: model "data pribadi/silsilah" (`tarombo.orang`,
  `tarombo.pernikahan`, `tarombo.pendidikan`, `tarombo.pekerjaan`, `tarombo.arsip`,
  `tarombo.usulan`) = anggota read-only (usulan: + create), pengurus & admin CRUD.
  Model "struktural/konfigurasi" (`tarombo.marga`, `tarombo.padan`, `tarombo.wilayah`,
  `tarombo.punguan`) = anggota/pengurus read-only, hanya admin CRUD.

## 7. Views & Navigasi

- **Menu**: `menu_tarombo_root` (groups=anggota) → **Anggota** (Daftar Anggota +
  Arsip), **Usulan** (Daftar Usulan), **Laporan** (Hitung Partuturan + Direktori
  Keahlian), **Konfigurasi** (groups=admin: Marga, Padan, Wilayah, Punguan).
- **PENTING — bug nyata**: `action_tarombo_orang` awalnya tidak mengunci
  `view_id`/`view_ids`. Begitu model `tarombo.orang` punya >1 list view (setelah
  Direktori Keahlian dibuat), Odoo memilih view "default" secara ambigu dan sempat
  menampilkan list read-only Direktori Keahlian di menu Anggota biasa (tombol "Baru"
  hilang). **Sudah diperbaiki** — `view_ids` dikunci eksplisit. **Aturan umum**: begitu
  model punya >1 view bertipe sama, SEMUA action untuk model itu wajib kunci
  `view_id`/`view_ids` eksplisit.
- **PENTING — one2many di dalam `<group>` butuh `colspan="2"`**: `<group>` Odoo default
  grid 2 kolom; field one2many/list yang dibungkus `<group string="...">` tanpa
  `colspan="2"` cuma dapat setengah lebar, bikin header kolom terpotong. Semua list
  embed di form `tarombo.orang` (Pernikahan, Anak, Pendidikan, Pekerjaan) sudah pakai
  `colspan="2"`; field `arsip_ids` aman karena tidak dibungkus `<group>` sama sekali.
- Form `tarombo.orang` sekarang 6 tab: **Identitas**, **Keluarga** (ayah, pernikahan
  dengan peringatan adat, anak — dikelompokkan per istri kalau `punya_istri_ganda`,
  tab "Anak" diberi judul group eksplisit), **Domisili**, **Riwayat**, **Arsip**,
  **Keabsahan**. Header form punya tombol "Pohon Silsilah".
- Search `tarombo.orang`: filter/groupby sundut, marga, jenis kelamin, bidang_kini,
  pendidikan_tertinggi.

## 8. Cara memulai kerja di modul ini

- Model baru → file di `models/`, daftar di `models/__init__.py`. Selection list lintas
  model (mis. `JENJANG_SELECTION` dari `tarombo_riwayat.py`) tinggal di-`import`
  langsung — Odoo tidak peduli urutan import Python untuk model independen.
- **>1 view bertipe sama untuk model yang sudah punya action lain** → cek ulang &
  kunci `view_id`/`view_ids` eksplisit di action baru DAN action lama.
- **Grup baru** → pastikan grup dasarnya implies `base.group_user` kalau untuk user
  biasa (`ir.model.access.csv` saja tidak cukup).
- **Sebelum `groups=` di field** → pikirkan dulu apakah field itu dipakai di domain
  action/filter yang harus bisa diakses grup lebih rendah.
- **One2many/list di dalam `<group>`** → selalu kasih `colspan="2"`, atau taruh di
  luar `<group>` sama sekali.
- **Aset JS pihak ketiga (ECharts, dll)** → vendor lokal ke `static/lib/`, cek dulu
  apakah modul lain di server sudah punya file yang sama sebelum minta didownload
  ulang. Referensikan sebagai variabel global di JS (bukan `import`) kalau library-nya
  bukan modul ES (UMD/IIFE bundle biasa).
- **Aturan adat yang berdampak ke validasi** (mis. larangan nikah semarga/padan) —
  jangan asumsikan dari ingatan sendiri, cek dulu sebelum implementasi (lihat
  `satu_keturunan`/`terikat_padan`/`peringatan_adat`). Defaultnya **peringatan, bukan
  blokir keras** — keputusan eksplisit karena sistem ini tugasnya merekam silsilah apa
  adanya, bukan jadi polisi adat.
## 9. Progres Impor Data Real: Silsilah Marga Silaen (technocraft.org)

> Bagian ini **bukan** dokumentasi kode modul, tapi catatan progres proyek data —
> supaya sesi kerja berikutnya bisa lanjut tanpa re-derive dari nol. Update terakhir:
> 2026-09-07.

**Sumber data**: [www.technocraft.org/tuansihubil](https://www.technocraft.org/tuansihubil/tarombo.cgi)
("Tarombo Online", dikelola sejak 1964) — situs publik silsilah keturunan Tuan Sihubil.
Fokus impor **hanya cabang marga Silaen**, bukan seluruh keturunan Tuan Sihubil (yang
jumlahnya ribuan lintas banyak marga).

**Rantai leluhur** (diimpor utuh termasuk saudara-saudaranya, sundut 1-4, supaya jelas
posisi Soddiraja di antara saudaranya):
Tuan Sihubil (man=1000201, sundut 1) → Sapala Tua alias Tappuk Na Bolon (man=1000301,
sundut 2, 3 bersaudara) → Raja Mataniari (man=1000302, sundut 3) → **Soddiraja alias
Silaen** (man=1000403, sundut 4, anak ke-5 dari 8 bersaudara — mulai dari sini marga
`Silaen` dipakai, sebelumnya `Tampubolon`).

**4 cabang besar** (anak langsung Soddiraja, sundut 5) dan statusnya:

| Cabang | man_id | Status laki-laki | Status Boru (perempuan) |
|---|---|---|---|
| Patuan Namora | 1000741 | ✅ tuntas | ✅ tuntas |
| Raja Panabungan | 1000421 | ✅ tuntas | ✅ tuntas |
| Raja Raum alias Siringkiron | 1000423 | ✅ tuntas (2 halaman Boru gagal permanen, minor) | ✅ tuntas (minor gap) |
| Ompu Sumindar | 1000420 | ✅ tuntas | ✅ tuntas |
| **Raja Panggomal alias Lumbandolok** | **1000422** | ⏳ **belum dimulai** (~62 titik) | ⏳ belum dimulai |

Total saat ini (medan **dan** live tersinkron sama persis): **4543 orang** (1375
perempuan), 140 marga, 1104 pernikahan.

**Cara kerja crawl** (halaman situs, bukan API):
- Descendants (`?lyr=7;wfe=Y;dgh=L;man=<ID>;act=tree`) — tabel HTML, indentasi kolom =
  level generasi, `<a act=pick_man>` = nama+man_id, `<i>soripadana boru X,Y</i>` = daftar
  marga istri (poligami dipisah koma), `<i>anak N</i>` = jumlah anak laki-laki tercatat.
  **Hanya anak laki-laki muncul di sini** (garis patrilineal) — dibatasi 7 generasi per
  panggilan, titik generasi ke-7 yang masih `anak N > 0` perlu di-drill ulang
  (`man=<id_baru>;act=tree`) sebagai akar baru, rekursif.
- Family (`?man=<ID>;act=sfam`) — tabel HTML polos (tanpa link), 3 seksi "Istri"/"Anak"/
  "**Boru**" (anak perempuan) format `"N  Nama br MargaAyah muli tu MargaSuami"` — nama
  personal istri kadang terisi di sini (situs Descendants cuma catat marga istri, tidak
  pernah nama). Harus dibuka **satu per satu per orang** (tidak ada versi tree-nya).
- **Situs pakai Cloudflare (managed challenge)** — `curl` polos kena 403. Solusi: ambil
  cookie `cf_clearance` dari browser user (DevTools → Application → Cookies →
  technocraft.org) + User-Agent yang sama, pasang di header request Python
  (`urllib.request`). Cookie **bukan soal expired waktu** — Cloudflare mendeteksi *pola
  akses otomatis* (banyak request cepat) dan mulai balas `Cf-Mitigated: challenge` di
  response header walau cookie masih valid. Perlu cookie baru berkala (kadang tiap
  ~20-700 request, tidak konsisten). Jeda 1.2-2 detik/request + auto-stop setelah 3x
  gagal beruntun (jangan terus menghajar server yang sudah menolak).

**Pipeline lengkap** (skrip disalin ke `D:\Document\SilsilahBatak\scripts\` — **bukan**
di source module ini/git. Berisi cookie & password server live hardcoded, jangan
disebarluaskan):
1. `crawl_branch.py <man_id>` — crawl Descendants 1 cabang sampai tuntas, update
   `tarombo_silaen_full.json` in-place (field: `man_id`, `name`, `sundut` absolut relatif
   Tuan Sihubil, `wives`, `ayah_man_id`, `jumlah_anak_tercatat`).
2. `crawl_family_branch.py <man_id> <output.json>` — crawl halaman Family 1 cabang,
   **resumable** (baca file existing, skip yang sudah, lanjut sisanya) — penting karena
   cookie sering mati di tengah jalan.
3. `import_incremental.py` — import orang **baru saja** (belum ada di
   `man_to_orang_id.json`) dari `tarombo_silaen_full.json` ke Odoo lokal **"medan"**,
   diproses level demi level (sundut naik, `Orang.create(vals_list)` per level, BUKAN
   satu-satu) supaya `ayah_id` self-reference selalu sudah ada duluan.
4. `import_family_branch.py` — import Boru + update `istri_nama` ke "medan" dari hasil
   langkah 2 (regex `"(nama) br (marga)( muli tu (marga_suami))?"`, urutan Boru
   dilanjutkan dari nomor urut anak laki-laki terakhir supaya tidak bentrok
   `_urutan_unik`).
5. `dump_full.py` — export SEMUA tarombo.* dari "medan" jadi satu JSON, tiap record
   dikasih **External ID** (`ir.model.data`, module `tarombo_import`, name
   `man_<man_id>`/`marga_<id>`/dst, auto-dibuat kalau belum ada) → `tarombo_dump_full.json`.
6. `sync_incremental.py` — kirim **selisih** dari dump ke server live via **XML-RPC**
   (bukan CSV import UI — lihat alasan di bawah), skip record yang xmlid-nya sudah ada
   di `medan_xmlid_to_live_id.json`, buat yang baru, update `istri_nama` yang berubah,
   lalu simpan lagi mapping-nya (mapping ini **wajib** dipertahankan antar-sesi, kalau
   hilang perlu `rekonstruksi_mapping_live.py` — cocokkan ulang by name+ayah_id
   berurutan sundut, hasilnya deterministik tapi butuh 1 RPC call per record).

**Kenapa sync ke live pakai XML-RPC langsung, bukan CSV import UI**: sempat dicoba CSV
export + import lewat UI Odoo, gagal dengan error *"No matching records found"* untuk
`ayah_id/id` meski External ID-nya benar dan konsisten — penyebabnya Odoo meng-import
file besar **per-batch** (field "Batch limit" di layar import), dan kalau baris anak
ada di batch yang diproses sebelum baris ayahnya (urutan baris di file tidak terjamin
topological), referensinya gagal ditemukan. Perbaikan (urutkan baris CSV by sundut
naik) mengurangi tapi tidak 100% menghilangkan masalah ini di file >3000 baris.
**XML-RPC langsung (`execute_kw` create satu-satu, urutan Python dijamin)** jauh lebih
andal dan ternyata lebih cepat (~3600 record ≈ 5-6 menit).

**Server live**: https://tarombo.selstudio.id, database `tarombo`, login admin
`rofianto507@gmail.com`. Akses SSH tersedia (key `.ppk` format PuTTY) tapi tidak jadi
dipakai — cukup XML-RPC dengan user/pass. **Jebakan XML-RPC**: `execute_kw(db, uid, pwd,
model, method, args, kwargs)` — domain untuk `search`/`search_read` masuk sebagai
**elemen pertama list `args`**, jangan dibungkus list ekstra (`[domain]`, bukan
`[[domain]]`), dan opsi seperti `fields=[...]` harus dikirim sebagai **keyword
argument** ke `execute_kw` (masuk `kwargs`), **bukan** sebagai dict positional
tambahan — kalau salah taruh sebagai args, error yang muncul menyesatkan
(`Invalid field 'fields' on <model>` atau `Domain() invalid item`).

**Data yang TIDAK tersedia dari sumber** (kosong secara sengaja, bukan bug import):
foto, tahun lahir/wafat, status hidup/wafat, alamat domisili, nama personal istri
(kalau halaman Family tidak menyebutkannya) — semua field ini valid untuk diisi
belakangan manual atau lewat alur Usulan.

Breaking change Odoo 19 yang sudah dikonfirmasi di server ini (jangan diulang):
  - `res.groups.category_id` → lewat `res.groups.privilege_id` (`res.groups.privilege`).
  - `res.users.groups_id` → `res.users.group_ids`.
  - `_check_recursion()` deprecated sejak 18.0 → pakai `_has_cycle()`.
  - `_sql_constraints = [...]` **sudah tidak dibaca sama sekali** (cuma log warning) →
    wajib pakai `models.Constraint(sql, message)`.
  - `unaccent=` bukan kwarg valid pada `fields.Char`.
  - View `<hierarchy>` butuh depend `web_hierarchy`, wajib punya
    `<templates><t t-name="hierarchy-box">...</t></templates>`.
  - Kanban modern pakai `<t t-name="card">` (bukan `t-name="kanban-box"` lama) dan
    `<field widget="image" invisible="...">` langsung (bukan helper `kanban_image()`).
