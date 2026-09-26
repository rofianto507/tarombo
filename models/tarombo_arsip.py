from odoo import api, fields, models

JENIS_ARSIP_SELECTION = [
    ('foto', 'Foto'),
    ('dokumen', 'Dokumen'),
    ('audio', 'Audio'),
    ('video', 'Video'),
    ('naskah', 'Naskah'),
]


class TaromboArsip(models.Model):
    _name = 'tarombo.arsip'
    _description = 'Arsip (Tarombo)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Nama', required=True, tracking=True)
    jenis = fields.Selection(JENIS_ARSIP_SELECTION, string='Jenis', tracking=True)
    orang_id = fields.Many2one('tarombo.orang', string='Orang', index=True, tracking=True)
    punguan_id = fields.Many2one('tarombo.punguan', string='Punguan', required=True, tracking=True)
    tahun_perkiraan = fields.Char(
        'Tahun (Perkiraan)', help='Banyak berkas lama hanya diketahui kisaran tahunnya', tracking=True)
    sumber = fields.Char('Sumber', tracking=True)
    keterangan = fields.Text('Keterangan')
    # Binary asli (tombol Upload sungguhan) — BUKAN Many2one ke ir.attachment,
    # yang tadinya membuat picker mencari attachment yang SUDAH ADA di seluruh
    # database (termasuk file teknis sistem), bukan tombol unggah file baru.
    berkas = fields.Binary('Berkas', required=True, attachment=True)
    berkas_nama = fields.Char('Nama Berkas')
    pratinjau = fields.Image(
        'Pratinjau', compute='_compute_pratinjau', max_width=512, max_height=512)
    publik = fields.Boolean('Boleh Dilihat Seluruh Anggota', default=True, tracking=True)

    @api.depends('jenis', 'berkas')
    def _compute_pratinjau(self):
        for r in self:
            r.pratinjau = r.berkas if r.jenis == 'foto' else False
