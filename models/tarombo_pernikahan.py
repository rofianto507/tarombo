from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TaromboPernikahan(models.Model):
    _name = 'tarombo.pernikahan'
    _description = 'Pernikahan (Tarombo)'
    _order = 'suami_id, urutan'

    suami_id = fields.Many2one(
        'tarombo.orang', string='Suami', required=True, index=True, ondelete='cascade')
    urutan = fields.Integer('Istri ke-', required=True, default=1)
    istri_nama = fields.Char('Nama Istri')
    istri_marga_id = fields.Many2one('tarombo.marga', string='Marga Istri', required=True)
    tahun = fields.Integer('Tahun')
    anak_ids = fields.One2many('tarombo.orang', 'pernikahan_id', string='Anak')
    peringatan_adat = fields.Char(compute='_compute_peringatan_adat')

    _urutan_unik = models.Constraint(
        'UNIQUE(suami_id, urutan)',
        'Nomor urut istri tidak boleh berulang pada orang yang sama.',
    )

    @api.depends('urutan', 'istri_nama')
    def _compute_display_name(self):
        for r in self:
            r.display_name = 'Istri ke-%s: %s' % (r.urutan, r.istri_nama or '')

    @api.depends('suami_id.marga_id', 'istri_marga_id')
    def _compute_peringatan_adat(self):
        # Peringatan saja, TIDAK memblokir penyimpanan: tugas sistem ini
        # merekam silsilah apa adanya, termasuk kasus yang secara adat
        # kontroversial, bukan menjadi polisi adat.
        for r in self:
            marga_suami = r.suami_id.marga_id
            marga_istri = r.istri_marga_id
            if not marga_suami or not marga_istri:
                r.peringatan_adat = False
            elif marga_suami.satu_keturunan(marga_istri):
                r.peringatan_adat = _(
                    'Peringatan adat: %(suami)s dan calon istri sama-sama dari garis marga '
                    '%(marga)s (dongan tubu). Menurut adat Batak, pernikahan semarga dianggap '
                    'seperti menikahi saudara sendiri.'
                ) % {'suami': r.suami_id.name, 'marga': marga_suami.name}
            elif marga_suami.terikat_padan(marga_istri):
                r.peringatan_adat = _(
                    'Peringatan adat: marga %(a)s dan %(b)s terikat sumpah padan leluhur, '
                    'sehingga secara adat juga dilarang saling menikahi.'
                ) % {'a': marga_suami.name, 'b': marga_istri.name}
            else:
                r.peringatan_adat = False

    @api.constrains('suami_id')
    def _cek_suami_laki(self):
        for r in self:
            if r.suami_id.jenis_kelamin != 'L':
                raise ValidationError(_('Suami pada pernikahan harus berjenis kelamin laki-laki.'))