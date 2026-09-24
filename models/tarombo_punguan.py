from odoo import api, fields, models


class TaromboPunguan(models.Model):
    _name = 'tarombo.punguan'
    _description = 'Punguan (Tarombo)'
    _order = 'name'

    # Punguan adalah komunitas/paguyuban lokal, tidak menentukan penomoran sundut.
    # Sundut dihitung dari leluhur acuan tunggal (ir.config_parameter 'tarombo.leluhur_acuan_id').

    name = fields.Char('Nama', required=True)
    kode = fields.Char('Kode')
    keterangan = fields.Text('Keterangan')
    wilayah_id = fields.Many2one('tarombo.wilayah', string='Kedudukan')
    pengurus_ids = fields.Many2many('res.users', string='Pengurus Punguan')
    aktif = fields.Boolean('Aktif', default=True)
    jumlah_anggota = fields.Integer('Jumlah Anggota', compute='_compute_jumlah_anggota')

    _kode_uniq = models.Constraint('UNIQUE(kode)', 'Kode punguan harus unik!')

    def _compute_jumlah_anggota(self):
        for punguan in self:
            punguan.jumlah_anggota = self.env['tarombo.orang'].search_count([
                ('punguan_id', '=', punguan.id),
            ])
