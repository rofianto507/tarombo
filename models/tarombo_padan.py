from odoo import fields, models


class TaromboPadan(models.Model):
    _name = 'tarombo.padan'
    _description = 'Padan (Sumpah Persaudaraan Antar-Marga)'
    _order = 'name'

    name = fields.Char(
        'Nama Padan', required=True,
        help='Mis. "Hutabarat - Silaban" atau "Pomparan Parna"')
    marga_ids = fields.Many2many('tarombo.marga', string='Marga Terikat')
    keterangan = fields.Text('Keterangan', help='Sumber/riwayat sumpah padan ini')
