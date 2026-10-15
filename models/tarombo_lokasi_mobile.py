from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .tarombo_orang import (
    normalisasi_email, normalisasi_telp, pesan_kontak_tidak_valid,
)


class TaromboOrang(models.Model):
    _inherit = 'tarombo.orang'

    # File terpisah dari tarombo_dashboard.py (yang pengurus-only) supaya
    # pengecualian akses di sini mudah diaudit sendiri, terpisah dari kode
    # dashboard yang punya alasan akses berbeda.

    @api.model
    def get_lokasi_kerabat(self):
        """Titik lokasi untuk peta "Kerabat Terdekat" di app mobile — HANYA
        orang yang berbagi_lokasi=True, terlepas siapa pemanggilnya (semua
        anggota melihat himpunan titik yang sama).

        sudo() sengaja dipakai: latitude/longitude dibatasi groups=pengurus di
        ORM, tapi pengecualian ini SEMPIT (satu method, satu kondisi filter
        eksplisit `berbagi_lokasi=True`, proyeksi field tetap) — bukan
        pelonggaran groups= pada field itu sendiri, dan TIDAK menambahkan
        anggota ke group_tarombo_pengurus dengan cara apa pun. Jarak ke lokasi
        pengguna dihitung di sisi client (dari GPS device), server tidak perlu
        tahu posisi pemanggil sama sekali.
        """
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            raise AccessError(_('Fitur ini khusus anggota Tarombo yang sudah login.'))
        # DINONAKTIFKAN: titik lokasi rumah per orang tidak lagi dikumpulkan
        # maupun ditampilkan. Metode dipertahankan (daftar kosong) agar aplikasi
        # versi lama yang masih memanggilnya tidak error. Pengganti: sebaran
        # jumlah anggota per wilayah, lihat get_sebaran_wilayah().
        return []

    # Level wilayah -> field domisili pada tarombo.orang.
    _SEBARAN_FIELD = {
        '1': 'provinsi_id',
        '2': 'kabupaten_id',
        '3': 'kecamatan_id',
        '4': 'desa_id',
    }

    @api.model
    def get_sebaran_wilayah(self, tingkat='2'):
        """Jumlah anggota per wilayah pada satu tingkat (1 provinsi,
        2 kabupaten/kota, 3 kecamatan, 4 desa/kelurahan), untuk peta "Sebaran
        Anggota" di app mobile.

        Hanya agregat (nama wilayah + jumlah) — tidak ada nama atau titik
        individu. sudo() sengaja dipakai agar anggota biasa bisa menghitung
        seluruh anggota; pengecualiannya sempit (satu method, hanya hitungan
        per wilayah). Koordinat wilayah diambil dari tarombo.wilayah; bila
        wilayah (mis. kecamatan/desa) belum punya koordinat, dipakai koordinat
        induk terdekat dan ditandai `perkiraan`.
        """
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            raise AccessError(_('Fitur ini khusus anggota Tarombo yang sudah login.'))
        tingkat = str(tingkat)
        fld = self._SEBARAN_FIELD.get(tingkat)
        if not fld:
            raise UserError(_('Tingkat wilayah tidak dikenal.'))
        orang = self.sudo()
        hasil = orang._read_group([(fld, '!=', False)], [fld], ['__count'])
        items = []
        for wilayah, jumlah in hasil:
            titik = wilayah
            while titik and not (titik.latitude and titik.longitude):
                titik = titik.induk_id
            items.append({
                'id': wilayah.id,
                'nama': wilayah.name,
                'nama_lengkap': wilayah.complete_name,
                'jumlah': jumlah,
                'lat': titik.latitude if titik else False,
                'lng': titik.longitude if titik else False,
                'perkiraan': bool(titik) and titik.id != wilayah.id,
            })
        items.sort(key=lambda x: (-x['jumlah'], x['nama']))
        return {
            'tingkat': tingkat,
            'total_anggota': orang.search_count([]),
            'total_berwilayah': sum(i['jumlah'] for i in items),
            'items': items,
        }

    @api.model
    def get_domisili_orang(self, orang_id):
        """Info domisili SATU orang tertentu, untuk tab 'Domisili' di halaman
        profil mobile. Method terpisah dari get_lokasi_kerabat() supaya
        halaman profil tidak perlu menarik seluruh daftar kerabat yang
        berbagi lokasi cuma untuk mengecek satu id.

        `alamat_jalan` dikembalikan TANPA syarat — keputusan eksplisit
        pengelola data bahwa alamat lengkap boleh dilihat seluruh anggota
        terverifikasi, beda dari lat/lng yang tetap mensyaratkan opt-in
        `berbagi_lokasi` (titik peta dianggap lebih sensitif daripada teks
        alamat karena bisa dipakai navigasi langsung ke lokasi).

        sudo() sengaja dipakai: alamat_jalan/latitude/longitude dibatasi
        groups=pengurus di ORM, tapi pengecualian ini SEMPIT (satu method,
        proyeksi field tetap) — bukan pelonggaran groups= pada field itu
        sendiri, dan TIDAK menambahkan anggota ke group_tarombo_pengurus.
        """
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            raise AccessError(_('Fitur ini khusus anggota Tarombo yang sudah login.'))
        orang = self.sudo().browse(orang_id)
        # Alamat jalan dan titik lokasi tidak lagi ditampilkan; kuncinya
        # dipertahankan (bernilai kosong) untuk aplikasi versi lama.
        return {'alamat_jalan': False, 'berbagi_lokasi': False, 'lat': False, 'lng': False}

    @api.model
    def get_kontak_orang(self, orang_id):
        """Nomor telepon & email kontak SATU orang, untuk tab Kontak di profil
        mobile — supaya kerabat bisa saling menghubungi.

        Hanya untuk akun TERVERIFIKASI: akun yang sudah tertaut ke data anggota
        (user_id terisi lewat klaim yang disetujui pengurus) atau pengurus ke
        atas. Akun yang belum tertaut menerima nilai kosong, bukan error, supaya
        layar profil tetap bisa dirender.

        sudo() sengaja dipakai: no_telp/email_kontak dibatasi groups=pengurus di
        ORM (tidak terlihat anggota biasa lewat search_read). Pengecualian ini
        SEMPIT — satu method, satu record, proyeksi dua field tetap, dengan
        pemeriksaan verifikasi di atasnya — bukan pelonggaran groups= pada field
        itu sendiri.
        """
        kosong = {'no_telp': False, 'email_kontak': False, 'terverifikasi': False}
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            return kosong
        terverifikasi = (
            self.env.user.has_group('tarombo.group_tarombo_pengurus')
            or bool(self.sudo().search_count([('user_id', '=', self.env.uid)])))
        if not terverifikasi:
            return kosong
        orang = self.sudo().browse(orang_id)
        if not orang.exists():
            return kosong
        return {
            'no_telp': orang.no_telp or False,
            'email_kontak': orang.email_kontak or False,
            # Penanda untuk aplikasi: tab Kontak hanya ditampilkan bila True.
            'terverifikasi': True,
        }

    @api.model
    def get_my_orang(self):
        """Resolusi "akun saya = orang mana di pohon" untuk app mobile, dipakai
        setelah login/klaim disetujui. sudo() aman: hanya mencocokkan user_id
        milik pemanggil sendiri (self.env.uid), tidak membocorkan data orang lain.
        """
        orang = self.sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not orang:
            return False
        return {
            'id': orang.id,
            'name': orang.name,
            'sundut': orang.sundut,
            'punya_foto': bool(orang.foto),
            'berbagi_lokasi': orang.berbagi_lokasi,
        }

    @api.model
    def set_berbagi_lokasi(self, aktif, lat=False, lng=False):
        """Toggle opt-in "Bagikan Lokasi ke Kerabat" untuk akun yang login —
        HANYA pada record tarombo.orang milik sendiri (user_id == uid).

        sudo() sengaja dipakai: anggota TIDAK punya perm_write sama sekali di
        tarombo.orang (lihat ir.model.access.csv) — bukan hanya latitude/
        longitude yang groups=pengurus, seluruh model tertutup untuk write
        anggota. Pengecualian ini sempit (field & record ditentukan di sini,
        bukan lewat parameter bebas dari client) dan TIDAK menambahkan
        anggota ke group_tarombo_pengurus dengan cara apa pun.

        Mengaktifkan (aktif=True) wajib menyertakan lat/lng dari GPS device
        saat itu juga — supaya tidak ada jeda di mana berbagi_lokasi=True
        tapi titiknya masih kosong/usang. Menonaktifkan tidak perlu koordinat.
        """
        orang = self.sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not orang:
            raise UserError(_('Akun Anda belum tertaut ke data orang mana pun.'))
        if aktif:
            if not lat or not lng:
                raise UserError(_('Titik lokasi GPS wajib diisi untuk mengaktifkan berbagi lokasi.'))
            orang.write({'berbagi_lokasi': True, 'latitude': lat, 'longitude': lng})
        else:
            orang.write({'berbagi_lokasi': False})
        return True

    # ── Profil sendiri (app mobile) ─────────────────────────────────────────
    # Anggota melengkapi data DIRINYA SENDIRI tanpa lewat usulan/pengurus:
    # foto, tanggal lahir, domisili. Nama, jenis kelamin, ayah, marga, dan
    # hubungan keluarga TETAP lewat tarombo.usulan — itu data bersama yang
    # mengubah bentuk pohon, bukan data pribadi.

    # Daftar putih field yang boleh ditulis pemilik akun. Sengaja konstanta
    # tertutup (bukan parameter dari client) — pola sama set_berbagi_lokasi().
    _PROFIL_SAYA_FIELDS = (
        'foto', 'tanggal_lahir', 'tahun_lahir',
        'provinsi_id', 'kabupaten_id', 'kecamatan_id', 'desa_id',
        'alamat_jalan', 'alamat_catatan',
        # Titik rumah di peta. Menulisnya TIDAK menyalakan berbagi lokasi —
        # tampil ke anggota lain tetap hanya bila berbagi_lokasi diaktifkan.
        'latitude', 'longitude',
        # Kontak pribadi: hanya pemilik & pengurus yang bisa melihatnya.
        'no_telp', 'email_kontak',
    )
    _PROFIL_SAYA_WILAYAH = (
        ('provinsi_id', '1'), ('kabupaten_id', '2'), ('kecamatan_id', '3'), ('desa_id', '4'),
    )

    def _profil_saya_orang(self):
        orang = self.sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not orang:
            raise UserError(_('Akun Anda belum tertaut ke data orang mana pun.'))
        return orang

    def _kelengkapan_profil(self):
        """Butir kelengkapan profil + persentasenya, untuk kartu di beranda
        app. Hanya butir yang bisa diisi pemilik akun sendiri."""
        self.ensure_one()
        butir = [
            ('foto', _('Foto profil'), bool(self.foto)),
            ('tanggal_lahir', _('Tahun lahir'), bool(self.tahun_lahir)),
            ('domisili', _('Domisili (kabupaten/kota)'), bool(self.kabupaten_id)),
            ('pendidikan', _('Riwayat pendidikan'), bool(self.pendidikan_ids)),
            ('pekerjaan', _('Riwayat pekerjaan'), bool(self.pekerjaan_ids)),
        ]
        selesai = sum(1 for b in butir if b[2])
        return {
            'persen': round(selesai * 100 / len(butir)),
            'selesai': selesai,
            'total': len(butir),
            'butir': [{'key': k, 'label': label, 'selesai': ok} for k, label, ok in butir],
        }

    @api.model
    def get_profil_saya(self):
        """Data profil milik akun yang login (termasuk field yang dibatasi
        groups=pengurus seperti tanggal_lahir & alamat_jalan — pemiliknya
        sendiri tentu boleh melihat datanya) + kelengkapannya. False bila
        akun belum tertaut ke orang mana pun."""
        orang = self.sudo().search([('user_id', '=', self.env.uid)], limit=1)
        if not orang:
            return False

        def m2o(rec):
            return [rec.id, rec.name] if rec else False

        return {
            'id': orang.id,
            'name': orang.name,
            'jenis_kelamin': orang.jenis_kelamin,
            'punya_foto': bool(orang.foto),
            'tanggal_lahir': orang.tanggal_lahir and orang.tanggal_lahir.isoformat() or False,
            'tahun_lahir': orang.tahun_lahir or False,
            'provinsi_id': m2o(orang.provinsi_id),
            'kabupaten_id': m2o(orang.kabupaten_id),
            'kecamatan_id': m2o(orang.kecamatan_id),
            'desa_id': m2o(orang.desa_id),
            'alamat_jalan': orang.alamat_jalan or False,
            'alamat_catatan': orang.alamat_catatan or False,
            'no_telp': orang.no_telp or False,
            'email_kontak': orang.email_kontak or False,
            'latitude': orang.latitude or False,
            'longitude': orang.longitude or False,
            'berbagi_lokasi': orang.berbagi_lokasi,
            'kelengkapan': orang._kelengkapan_profil(),
        }

    @api.model
    def update_profil_saya(self, vals):
        """Tulis data profil milik akun yang login. HANYA field di
        _PROFIL_SAYA_FIELDS dan HANYA record milik sendiri (user_id == uid).

        sudo() sengaja dipakai (anggota tidak punya perm_write di
        tarombo.orang). Pengecualiannya sempit: record ditentukan di sini,
        field disaring daftar putih, dan rantai wilayah divalidasi supaya
        tiap tingkat benar-benar anak dari tingkat di atasnya.
        """
        orang = self._profil_saya_orang()
        tulis = {k: v for k, v in (vals or {}).items() if k in self._PROFIL_SAYA_FIELDS}
        if not tulis:
            return self.get_profil_saya()

        if tulis.get('tahun_lahir'):
            tahun = int(tulis['tahun_lahir'])
            if tahun > fields.Date.context_today(self).year:
                raise UserError(_('Tahun lahir tidak boleh di masa depan.'))
            if tahun < 1000:
                raise UserError(_('Tahun lahir tidak valid.'))
            tulis['tahun_lahir'] = tahun
        elif tulis.get('tanggal_lahir'):
            # Aplikasi versi lama masih mengirim tanggal; cukup tahunnya yang dipakai.
            tanggal = fields.Date.to_date(tulis['tanggal_lahir'])
            if tanggal > fields.Date.context_today(self):
                raise UserError(_('Tanggal lahir tidak boleh di masa depan.'))
            tulis['tanggal_lahir'] = tanggal

        # Wilayah: hasil akhir (nilai baru menimpa nilai lama) harus berantai
        # benar. Tingkat yang lebih rendah dikosongkan bila induknya berubah
        # dan tidak dikirim ulang; induk diisi otomatis dari anak bila kosong.
        if any(nama in tulis for nama, _t in self._PROFIL_SAYA_WILAYAH):
            Wilayah = self.env['tarombo.wilayah'].sudo()
            hasil = {}
            for nama, tingkat in self._PROFIL_SAYA_WILAYAH:
                nilai = tulis[nama] if nama in tulis else orang[nama].id
                rec = Wilayah.browse(nilai or [])
                if rec and (not rec.exists() or rec.tingkat != tingkat):
                    raise UserError(_('Pilihan wilayah tidak sesuai tingkatnya.'))
                hasil[nama] = rec
            urut = [n for n, _t in self._PROFIL_SAYA_WILAYAH]
            # Isi induk dari anak (mis. pilih desa saja -> kecamatan s.d. provinsi ikut).
            for i in range(len(urut) - 1, 0, -1):
                if hasil[urut[i]] and not hasil[urut[i - 1]]:
                    hasil[urut[i - 1]] = hasil[urut[i]].induk_id
            # Buang anak yang bukan milik induknya.
            for i in range(1, len(urut)):
                anak, induk = hasil[urut[i]], hasil[urut[i - 1]]
                if anak and anak.induk_id != induk:
                    if urut[i] in tulis and tulis[urut[i]]:
                        raise UserError(_('%s bukan bagian dari %s.') % (anak.name, induk.name or '-'))
                    hasil[urut[i]] = Wilayah
            for nama in urut:
                tulis[nama] = hasil[nama].id or False

        # Titik rumah: latitude & longitude harus dikirim berpasangan. Keduanya
        # kosong (False/0) = hapus titik, dan berbagi lokasi ikut dimatikan
        # supaya tidak ada status "dibagikan" tanpa titik.
        if 'latitude' in tulis or 'longitude' in tulis:
            lat, lng = tulis.get('latitude'), tulis.get('longitude')
            if not lat and not lng:
                tulis['latitude'] = tulis['longitude'] = False
                tulis['berbagi_lokasi'] = False
            else:
                if not lat or not lng:
                    raise UserError(_('Lintang dan bujur harus diisi bersamaan.'))
                try:
                    lat, lng = float(lat), float(lng)
                except (TypeError, ValueError):
                    raise UserError(_('Koordinat tidak valid.'))
                if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                    raise UserError(_('Koordinat di luar rentang yang valid.'))
                tulis['latitude'], tulis['longitude'] = lat, lng

        if 'no_telp' in tulis:
            tulis['no_telp'] = normalisasi_telp(tulis['no_telp'])
        if 'email_kontak' in tulis:
            tulis['email_kontak'] = normalisasi_email(tulis['email_kontak'])
        if 'no_telp' in tulis or 'email_kontak' in tulis:
            pesan = pesan_kontak_tidak_valid(
                tulis.get('no_telp', orang.no_telp), tulis.get('email_kontak', orang.email_kontak))
            if pesan:
                raise UserError(pesan)

        for teks in ('alamat_jalan', 'alamat_catatan'):
            if teks in tulis:
                tulis[teks] = (tulis[teks] or '').strip() or False

        # Pemilik akun yang aktif memakai aplikasi jelas masih hidup.
        if not orang.masih_hidup:
            tulis['masih_hidup'] = True

        orang.write(tulis)
        return self.get_profil_saya()
