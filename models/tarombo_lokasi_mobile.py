from odoo import api, models, _
from odoo.exceptions import AccessError, UserError


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
        orang = self.sudo().search([
            ('berbagi_lokasi', '=', True),
            ('latitude', '!=', 0),
            ('longitude', '!=', 0),
        ])
        return [{
            'id': o.id,
            'name': o.name,
            'lat': o.latitude,
            'lng': o.longitude,
            'sundut': o.sundut,
            'jenis_kelamin': o.jenis_kelamin,
            'punguan': o.punguan_id.name,
            'punya_foto': bool(o.foto),
        } for o in orang]

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
        if not orang.exists():
            return {'alamat_jalan': False, 'berbagi_lokasi': False, 'lat': False, 'lng': False}
        ada_lokasi = bool(orang.berbagi_lokasi and orang.latitude and orang.longitude)
        return {
            'alamat_jalan': orang.alamat_jalan or False,
            'berbagi_lokasi': ada_lokasi,
            'lat': orang.latitude if ada_lokasi else False,
            'lng': orang.longitude if ada_lokasi else False,
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
