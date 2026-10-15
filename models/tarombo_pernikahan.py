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
    status_adat = fields.Char(
        'Pemeriksaan Adat', compute='_compute_status_adat',
        help='Hasil pemeriksaan otomatis marga suami dan marga istri terhadap '
             'aturan dongan tubu dan padan. Kolom ini hanya tampil sebagai '
             'informasi dan tidak pernah menolak penyimpanan.')

    _urutan_unik = models.Constraint(
        'UNIQUE(suami_id, urutan)',
        'Nomor urut istri tidak boleh berulang pada orang yang sama.',
    )

    @api.depends('urutan', 'istri_nama')
    def _compute_display_name(self):
        for r in self:
            r.display_name = 'Istri ke-%s: %s' % (
                r.urutan, r.istri_nama or _('(nama belum diketahui)'))

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

    def _marga_dalam_nama(self, nama):
        """Marga yang namanya muncul sebagai kata di `nama` istri (mis. "Sinta
        Silaen" -> Silaen). Hanya untuk pengingat: pemeriksaan adat tetap
        memakai kolom Marga Istri, bukan hasil tebakan dari nama."""
        kata = {k.strip().lower() for k in (nama or '').replace(',', ' ').split() if k.strip()}
        if not kata:
            return self.env['tarombo.marga']
        semua = self.env['tarombo.marga'].search([])
        return semua.filtered(lambda m: (m.name or '').strip().lower() in kata)

    @api.depends('suami_id.marga_id', 'istri_marga_id', 'istri_nama', 'peringatan_adat')
    def _compute_status_adat(self):
        # Kolom peringatan_adat kosong bila tidak ada masalah ATAU bila marga
        # belum terisi; bagi pengurus keduanya tampak sama. Di sini keadaan
        # dibedakan supaya kolom tidak terlihat rusak, dan nama istri yang
        # memuat marga berbeda dari Marga Istri ikut diingatkan.
        for r in self:
            dalam_nama = r._marga_dalam_nama(r.istri_nama)
            beda = dalam_nama - r.istri_marga_id if r.istri_marga_id else dalam_nama
            if r.peringatan_adat:
                r.status_adat = r.peringatan_adat
            elif beda and r.istri_marga_id:
                r.status_adat = _(
                    'Periksa: nama istri memuat marga %(nama)s, sedangkan Marga Istri '
                    'diisi %(isi)s. Pemeriksaan adat memakai kolom Marga Istri.'
                ) % {'nama': ', '.join(sorted(set(beda.mapped('name')))), 'isi': r.istri_marga_id.name}
            elif not r.istri_marga_id:
                r.status_adat = _('Belum diperiksa: marga istri belum diisi.')
            elif not r.suami_id.marga_id:
                r.status_adat = _('Belum diperiksa: marga suami belum diisi.')
            else:
                r.status_adat = _('Sesuai: tidak ada larangan semarga atau padan.')

    def unlink(self):
        # Menghapus pernikahan yang masih punya anak akan memutus tautan
        # "dari istri ke-" dan mengosongkan nama/marga ibu semua anaknya.
        # Tolak dengan pesan jelas; baris tanpa anak (mis. data uji) bebas dihapus.
        for r in self:
            if r.anak_ids:
                raise ValidationError(_(
                    'Istri ke-%(urutan)s (%(nama)s) masih memiliki %(n)d anak. '
                    'Pindahkan anak tersebut ke istri lain atau kosongkan isian '
                    '"Dari istri ke-" pada anaknya sebelum menghapus.'
                ) % {'urutan': r.urutan, 'nama': r.istri_nama or '-', 'n': len(r.anak_ids)})
        return super().unlink()

    @api.constrains('suami_id')
    def _cek_suami_laki(self):
        for r in self:
            if r.suami_id.jenis_kelamin != 'L':
                raise ValidationError(_('Suami pada pernikahan harus berjenis kelamin laki-laki.'))