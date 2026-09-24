from odoo import api, models, _
from odoo.exceptions import AccessError


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
