from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

TINGKAT_SELECTION = [
    ('1', 'Provinsi'),
    ('2', 'Kabupaten/Kota'),
    ('3', 'Kecamatan'),
    ('4', 'Desa/Kelurahan'),
]


class TaromboWilayah(models.Model):
    _name = 'tarombo.wilayah'
    _description = 'Wilayah Administratif (Tarombo)'
    _parent_name = 'induk_id'
    _parent_store = True
    _order = 'kode, name'
    _rec_names_search = ['name', 'kode', 'complete_name']

    kode = fields.Char('Kode', index=True, help='Kode Kemendagri')
    name = fields.Char('Nama', required=True, index=True)
    tingkat = fields.Selection(
        TINGKAT_SELECTION, string='Tingkat', required=True, index=True)
    induk_id = fields.Many2one(
        'tarombo.wilayah', string='Induk', index=True, ondelete='restrict')
    parent_path = fields.Char(index=True)
    kode_pos = fields.Char('Kode Pos')
    latitude = fields.Float('Latitude', digits=(10, 7))
    longitude = fields.Float('Longitude', digits=(10, 7))
    complete_name = fields.Char(
        string='Nama Lengkap', compute='_compute_complete_name', recursive=True, store=True)
    tingkat_induk = fields.Selection(
        TINGKAT_SELECTION, compute='_compute_tingkat_induk',
        help='Tingkat yang wajib dimiliki induk_id — dipakai buat filter domain di view.')

    @api.depends('name', 'induk_id.complete_name')
    def _compute_complete_name(self):
        for wilayah in self:
            if wilayah.induk_id:
                wilayah.complete_name = '%s / %s' % (wilayah.induk_id.complete_name, wilayah.name)
            else:
                wilayah.complete_name = wilayah.name

    @api.depends('tingkat')
    def _compute_tingkat_induk(self):
        for wilayah in self:
            wilayah.tingkat_induk = str(int(wilayah.tingkat) - 1) if wilayah.tingkat and wilayah.tingkat != '1' else False

    @api.constrains('tingkat', 'induk_id')
    def _check_tingkat_induk(self):
        for wilayah in self:
            if wilayah.tingkat == '1':
                if wilayah.induk_id:
                    raise ValidationError(_('Wilayah tingkat Provinsi tidak boleh punya induk.'))
            else:
                if not wilayah.induk_id:
                    raise ValidationError(_('Wilayah selain Provinsi wajib punya induk.'))
                if int(wilayah.tingkat) != int(wilayah.induk_id.tingkat) + 1:
                    raise ValidationError(_(
                        'Tingkat wilayah "%(name)s" harus tepat satu tingkat di bawah induknya '
                        '"%(induk)s".', name=wilayah.name, induk=wilayah.induk_id.name,
                    ))
