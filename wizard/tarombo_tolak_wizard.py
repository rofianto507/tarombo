from odoo import fields, models


class TaromboTolakWizard(models.TransientModel):
    _name = 'tarombo.tolak.wizard'
    _description = 'Alasan Penolakan (Usulan / Klaim Akun)'

    # res_model/res_id generik (bukan Many2one usulan_id/klaim_id terpisah)
    # supaya SATU wizard ini dipakai ulang untuk tarombo.usulan DAN
    # tarombo.klaim_akun — keduanya sama-sama butuh "isi alasan dulu sebelum
    # tolak", tapi beda model.
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    alasan_tolak = fields.Text('Alasan Penolakan', required=True)

    def action_konfirmasi(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        record.alasan_tolak = self.alasan_tolak
        record.action_tolak()
        return {'type': 'ir.actions.act_window_close'}
