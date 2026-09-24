from odoo import fields, models

JENJANG_SELECTION = [
    ('sd', 'SD'),
    ('smp', 'SMP'),
    ('sma', 'SMA'),
    ('d1', 'D1'),
    ('d3', 'D3'),
    ('d4', 'D4'),
    ('s1', 'S1'),
    ('s2', 'S2'),
    ('s3', 'S3'),
    ('lain', 'Lain-lain'),
]

BIDANG_SELECTION = [
    ('tani', 'Pertanian'),
    ('dagang', 'Perdagangan'),
    ('asn', 'ASN'),
    ('swasta', 'Swasta'),
    ('wiraswasta', 'Wiraswasta'),
    ('pendidik', 'Pendidik'),
    ('kesehatan', 'Kesehatan'),
    ('rohani', 'Rohaniwan'),
    ('lain', 'Lain-lain'),
]


class TaromboPendidikan(models.Model):
    _name = 'tarombo.pendidikan'
    _description = 'Riwayat Pendidikan (Tarombo)'
    _order = 'orang_id, tahun_masuk'

    orang_id = fields.Many2one(
        'tarombo.orang', string='Orang', required=True, index=True, ondelete='cascade')
    jenjang = fields.Selection(JENJANG_SELECTION, string='Jenjang', required=True)
    institusi = fields.Char('Institusi', required=True)
    jurusan = fields.Char('Jurusan')
    wilayah_id = fields.Many2one(
        'tarombo.wilayah', string='Wilayah', domain=[('tingkat', 'in', ['1', '2'])])
    tahun_masuk = fields.Integer('Tahun Masuk')
    tahun_lulus = fields.Integer('Tahun Lulus')
    lulus = fields.Boolean('Lulus', default=True)


class TaromboPekerjaan(models.Model):
    _name = 'tarombo.pekerjaan'
    _description = 'Riwayat Pekerjaan (Tarombo)'
    _order = 'orang_id, tahun_mulai desc'

    orang_id = fields.Many2one(
        'tarombo.orang', string='Orang', required=True, index=True, ondelete='cascade')
    jabatan = fields.Char('Jabatan', required=True)
    instansi = fields.Char('Instansi')
    bidang = fields.Selection(BIDANG_SELECTION, string='Bidang')
    wilayah_id = fields.Many2one('tarombo.wilayah', string='Wilayah')
    tahun_mulai = fields.Integer('Tahun Mulai')
    tahun_selesai = fields.Integer('Tahun Selesai')
    sekarang = fields.Boolean('Masih Berjalan')