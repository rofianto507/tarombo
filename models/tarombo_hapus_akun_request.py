from odoo import models, fields


class TaromboHapusAkunRequest(models.Model):
    _name = 'tarombo.hapus_akun_request'
    _description = 'Permintaan Hapus Akun'
    _order = 'tanggal_request desc'

    user_id = fields.Many2one('res.users', string='Pengguna', ondelete='set null')
    nama = fields.Char(string='Nama', required=True)
    login = fields.Char(string='Login / Email', required=True)
    alasan = fields.Text(string='Alasan (opsional)')
    tanggal_request = fields.Datetime(string='Tanggal Permintaan', default=fields.Datetime.now)
    state = fields.Selection([
        ('pending', 'Menunggu Diproses'),
        ('processed', 'Sudah Diproses'),
    ], string='Status', default='pending', required=True)
    catatan_admin = fields.Text(string='Catatan Admin')
    tanggal_proses = fields.Datetime(string='Tanggal Diproses')

    def action_proses(self):
        self.write({
            'state': 'processed',
            'tanggal_proses': fields.Datetime.now(),
        })
