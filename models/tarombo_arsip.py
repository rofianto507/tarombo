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
    # Satu arsip bisa terikat ke banyak anggota (mis. foto keluarga, naskah
    # silsilah yang memuat beberapa orang).
    orang_ids = fields.Many2many(
        'tarombo.orang', 'tarombo_arsip_orang_rel', 'arsip_id', 'orang_id',
        string='Orang Terkait', tracking=True)
    # KOMPATIBILITAS aplikasi mobile versi lama (<= 1.0.4), yang membaca dan
    # menulis `orang_id` tunggal dan membaca `punguan_id`. Jangan dihapus
    # selama versi itu masih beredar. Tidak ditampilkan di form admin. Nilainya
    # dijaga selalu salah satu dari orang_ids (lihat create/write).
    orang_id = fields.Many2one(
        'tarombo.orang', string='Orang Utama (lama)', index=True,
        help='Dipertahankan untuk aplikasi mobile versi lama. Gunakan Orang Terkait.')
    punguan_id = fields.Many2one(
        'tarombo.punguan', string='Punguan (lama)',
        help='Tidak lagi dipakai; dipertahankan untuk aplikasi mobile versi lama.')
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('orang_id') and not vals.get('orang_ids'):
                # Aplikasi lama: hanya mengirim satu orang.
                vals['orang_ids'] = [(4, vals['orang_id'])]
        records = super().create(vals_list)
        for rec, vals in zip(records, vals_list):
            if not vals.get('orang_id') and rec.orang_ids:
                # Penyelarasan internal: anggota tidak punya hak tulis pada arsip,
                # tetapi boleh membuatnya. Tanpa sudo(), create oleh anggota gagal.
                rec.sudo().orang_id = rec.orang_ids[0]
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'orang_ids' in vals and 'orang_id' not in vals:
            for rec in self:
                if rec.orang_id not in rec.orang_ids:
                    rec.sudo().orang_id = rec.orang_ids[:1]
        elif vals.get('orang_id') and 'orang_ids' not in vals:
            for rec in self:
                if vals['orang_id'] not in rec.orang_ids.ids:
                    rec.sudo().orang_ids = [(4, vals['orang_id'])]
        return res

    @api.depends('jenis', 'berkas')
    def _compute_pratinjau(self):
        for r in self:
            r.pratinjau = r.berkas if r.jenis == 'foto' else False
