from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TaromboMarga(models.Model):
    _name = 'tarombo.marga'
    _description = 'Marga (Tarombo)'
    _parent_name = 'marga_induk_id'
    _parent_store = True
    _order = 'complete_name'
    _rec_names_search = ['name', 'complete_name']

    name = fields.Char('Nama', required=True, index=True)
    kode = fields.Char('Kode')
    marga_induk_id = fields.Many2one(
        'tarombo.marga', string='Marga Induk', index=True, ondelete='restrict')
    parent_path = fields.Char(index=True)
    kelompok = fields.Selection([
        ('toba', 'Toba'),
        ('karo', 'Karo'),
        ('simalungun', 'Simalungun'),
        ('mandailing', 'Mandailing'),
        ('angkola', 'Angkola'),
        ('pakpak', 'Pakpak'),
    ], string='Kelompok')
    keterangan = fields.Text('Keterangan')
    anak_ids = fields.One2many('tarombo.marga', 'marga_induk_id', string='Anak Marga')
    complete_name = fields.Char(
        string='Nama Lengkap', compute='_compute_complete_name', recursive=True, store=True)
    jumlah_anggota = fields.Integer('Jumlah Anggota', compute='_compute_jumlah_anggota')

    _kode_uniq = models.Constraint('UNIQUE(kode)', 'Kode marga harus unik!')

    @api.depends('name', 'marga_induk_id.complete_name')
    def _compute_complete_name(self):
        for marga in self:
            if marga.marga_induk_id:
                marga.complete_name = '%s / %s' % (marga.marga_induk_id.complete_name, marga.name)
            else:
                marga.complete_name = marga.name

    def _compute_jumlah_anggota(self):
        for marga in self:
            marga.jumlah_anggota = self.env['tarombo.orang'].search_count([
                ('marga_id', 'child_of', marga.id),
            ])

    @api.constrains('marga_induk_id')
    def _check_marga_induk_recursion(self):
        if self._has_cycle():
            raise ValidationError(_('Marga induk tidak boleh membentuk siklus (marga tidak bisa menjadi leluhur dirinya sendiri).'))

    def satu_keturunan(self, lain):
        """True bila keduanya berasal dari akar marga yang sama (dongan tubu).

        Mencakup: salah satu leluhur marga yang lain, keduanya sama persis,
        maupun sekadar dua cabang berbeda dari marga akar yang sama (mis.
        Silaen dan Baringbing sama-sama anak Tampubolon) — secara adat
        ketiganya tetap dianggap satu marga/dongan tubu, bukan hanya relasi
        leluhur-keturunan langsung.
        """
        self.ensure_one()
        lain.ensure_one()
        akar_a = (self.parent_path or '').strip('/').split('/')[:1]
        akar_b = (lain.parent_path or '').strip('/').split('/')[:1]
        return bool(akar_a and akar_a == akar_b)

    def terikat_padan(self, lain):
        """True bila dua marga (berbeda akar) terikat sumpah padan leluhur."""
        self.ensure_one()
        lain.ensure_one()
        if self.id == lain.id:
            return False
        return bool(self.env['tarombo.padan'].search_count([
            ('marga_ids', '=', self.id),
            ('marga_ids', '=', lain.id),
        ]))
