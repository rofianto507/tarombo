from odoo import fields, models


class TaromboBidang(models.Model):
    _name = 'tarombo.bidang'
    _description = 'Bidang Pekerjaan'
    _order = 'name'

    name = fields.Char('Nama', required=True, index=True)
    keterangan = fields.Text('Keterangan')

    _name_uniq = models.Constraint('UNIQUE(name)', 'Nama bidang sudah ada, tidak boleh duplikat.')
