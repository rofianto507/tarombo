from odoo import fields, models


class TaromboPartuturanWizard(models.TransientModel):
    _name = 'tarombo.partuturan.wizard'
    _description = 'Hitung Partuturan'

    orang_a_id = fields.Many2one('tarombo.orang', string='Orang A', required=True)
    orang_b_id = fields.Many2one('tarombo.orang', string='Orang B', required=True)

    anc_id = fields.Many2one('tarombo.orang', string='Leluhur Bersama', readonly=True)
    sebutan_a = fields.Char('B memanggil A', readonly=True)
    sebutan_b = fields.Char('A memanggil B', readonly=True)
    senior_a = fields.Boolean('A Berkedudukan Lebih Tinggi', readonly=True)
    jarak = fields.Integer('Selisih Sundut', readonly=True)
    keterangan = fields.Text('Keterangan', readonly=True)
    jalur_a_ids = fields.Many2many(
        'tarombo.orang', 'tarombo_partuturan_wizard_jalur_a_rel', 'wizard_id', 'orang_id',
        string='Jalur Leluhur Bersama ke A', readonly=True)
    jalur_b_ids = fields.Many2many(
        'tarombo.orang', 'tarombo_partuturan_wizard_jalur_b_rel', 'wizard_id', 'orang_id',
        string='Jalur Leluhur Bersama ke B', readonly=True)

    def action_hitung(self):
        self.ensure_one()
        hasil = self.orang_a_id.hitung_partuturan(self.orang_b_id)
        self.write({
            'anc_id': hasil['anc'].id if hasil['anc'] else False,
            'sebutan_a': hasil['sebutan_a'],
            'sebutan_b': hasil['sebutan_b'],
            'senior_a': hasil['senior_a'],
            'jarak': hasil['jarak'],
            'keterangan': hasil['keterangan'],
            'jalur_a_ids': [(6, 0, hasil['jalur_a'].ids)],
            'jalur_b_ids': [(6, 0, hasil['jalur_b'].ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
