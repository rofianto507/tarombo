from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

JENIS_SELECTION = [
    ('tambah', 'Tambah'),
    ('koreksi', 'Koreksi'),
    ('lengkapi', 'Lengkapi'),
]

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('diajukan', 'Diajukan'),
    ('disetujui', 'Disetujui'),
    ('ditolak', 'Ditolak'),
]

JENIS_KELAMIN_SELECTION = [
    ('L', 'Laki-laki'),
    ('P', 'Perempuan'),
]

MASIH_HIDUP_SELECTION = [
    ('ya', 'Ya'),
    ('tidak', 'Tidak'),
]

# Pemetaan usul_* -> field tarombo.orang. Dipetakan ke provinsi/kabupaten/
# kecamatan/desa_id langsung (bukan wilayah_id yang compute+store) supaya
# bisa langsung ditulis lewat write()/create().
USUL_MUATAN_MAP = {
    'usul_nama': 'name',
    'usul_foto': 'foto',
    'usul_jenis_kelamin': 'jenis_kelamin',
    'usul_urutan': 'urutan',
    'usul_tahun_lahir': 'tahun_lahir',
    'usul_provinsi_id': 'provinsi_id',
    'usul_kabupaten_id': 'kabupaten_id',
    'usul_kecamatan_id': 'kecamatan_id',
    'usul_desa_id': 'desa_id',
    'usul_alamat_jalan': 'alamat_jalan',
    'usul_latitude': 'latitude',
    'usul_longitude': 'longitude',
    'usul_suami_nama': 'suami_nama',
    'usul_suami_marga_id': 'suami_marga_id',
    'catatan': 'catatan',
}


class TaromboUsulan(models.Model):
    _name = 'tarombo.usulan'
    _description = 'Usulan Perubahan Tarombo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='Baru', readonly=True, copy=False)
    punguan_id = fields.Many2one('tarombo.punguan', string='Punguan', required=True)
    active = fields.Boolean(default=True)
    jenis = fields.Selection(JENIS_SELECTION, string='Jenis', required=True, tracking=True)
    state = fields.Selection(
        STATE_SELECTION, string='Status', default='draft', tracking=True, index=True)

    # Sasaran
    orang_id = fields.Many2one(
        'tarombo.orang', string='Orang (sasaran koreksi/lengkapi)')
    ayah_id = fields.Many2one(
        'tarombo.orang', string='Ayah (sasaran penambahan)')
    pernikahan_id = fields.Many2one(
        'tarombo.pernikahan', string='Dari Istri ke-',
        domain="[('suami_id', '=', ayah_id)]")

    # Muatan usulan
    usul_nama = fields.Char('Nama')
    usul_foto = fields.Image('Foto', max_width=1024, max_height=1024)
    usul_jenis_kelamin = fields.Selection(JENIS_KELAMIN_SELECTION, string='Jenis Kelamin')
    usul_masih_hidup = fields.Selection(MASIH_HIDUP_SELECTION, string='Masih Hidup')
    usul_urutan = fields.Integer('Anak ke-')
    usul_tahun_lahir = fields.Integer('Tahun Lahir')
    usul_provinsi_id = fields.Many2one(
        'tarombo.wilayah', string='Provinsi', domain=[('tingkat', '=', '1')])
    usul_kabupaten_id = fields.Many2one(
        'tarombo.wilayah', string='Kabupaten/Kota',
        domain="[('tingkat', '=', '2'), ('induk_id', '=?', usul_provinsi_id)]")
    usul_kecamatan_id = fields.Many2one(
        'tarombo.wilayah', string='Kecamatan',
        domain="[('tingkat', '=', '3'), ('induk_id', '=?', usul_kabupaten_id)]")
    usul_desa_id = fields.Many2one(
        'tarombo.wilayah', string='Desa/Kelurahan',
        domain="[('tingkat', '=', '4'), ('induk_id', '=?', usul_kecamatan_id)]")
    usul_alamat_jalan = fields.Char('Alamat Lengkap')
    usul_latitude = fields.Float('Latitude', digits=(10, 7))
    usul_longitude = fields.Float('Longitude', digits=(10, 7))
    usul_suami_nama = fields.Char('Nama Suami')
    usul_suami_marga_id = fields.Many2one('tarombo.marga', string='Marga Suami')
    catatan = fields.Text('Catatan')

    # Jejak
    sumber_ket = fields.Char('Sumber Keterangan', required=True)
    pengusul_id = fields.Many2one(
        'res.users', string='Pengusul', default=lambda self: self.env.user, readonly=True)
    tanggal_ajukan = fields.Datetime('Tanggal Diajukan', readonly=True)
    peninjau_id = fields.Many2one('res.users', string='Peninjau', readonly=True)
    tanggal_tinjau = fields.Datetime('Tanggal Ditinjau', readonly=True)
    alasan_tolak = fields.Text('Alasan Penolakan')
    orang_hasil_id = fields.Many2one(
        'tarombo.orang', string='Hasil', readonly=True, ondelete='set null')
    lampiran_ids = fields.Many2many('ir.attachment', string='Lampiran')

    @api.onchange('orang_id')
    def _onchange_orang_id(self):
        # Isi Muatan Usulan dengan data terkini orang sasaran, supaya pengusul
        # tinggal mengedit field yang mau diperbarui saja dan bisa langsung
        # lihat data mana yang berubah — bukan menebak dari form kosong.
        if not self.orang_id or self.jenis == 'tambah':
            return
        o = self.orang_id
        self.usul_nama = o.name
        self.usul_foto = o.foto
        self.usul_jenis_kelamin = o.jenis_kelamin
        self.usul_masih_hidup = 'ya' if o.masih_hidup else 'tidak'
        self.usul_urutan = o.urutan
        self.usul_provinsi_id = o.provinsi_id
        self.usul_kabupaten_id = o.kabupaten_id
        self.usul_kecamatan_id = o.kecamatan_id
        self.usul_desa_id = o.desa_id
        self.usul_suami_nama = o.suami_nama
        self.usul_suami_marga_id = o.suami_marga_id
        # tahun_lahir, alamat_jalan, latitude & longitude dibatasi groups=pengurus
        # di tarombo.orang; cuma diisi otomatis kalau pengusulnya memang pengurus
        # ke atas, supaya anggota biasa yang bikin usulan tidak jadi bisa
        # mengintip data tersembunyi itu lewat prefill ini.
        if self.env.user.has_group('tarombo.group_tarombo_pengurus'):
            self.usul_tahun_lahir = o.tahun_lahir
            self.usul_alamat_jalan = o.alamat_jalan
            self.usul_latitude = o.latitude
            self.usul_longitude = o.longitude

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarombo.usulan') or 'Baru'
        return super().create(vals_list)

    def _muatan(self):
        """Kembalikan dict usul_* -> field tarombo.orang, hanya yang benar-benar diisi."""
        self.ensure_one()
        # Jenis kelamin acuan: dari usulan kalau ada (jenis 'tambah' atau usulan
        # koreksi jenis kelamin), kalau tidak dari data orang sasaran yang sudah
        # ada. Dipakai buat jaga suami_nama/suami_marga_id tidak ikut ditulis ke
        # data laki-laki meski somehow field itu terisi (mis. lewat import data),
        # bukan cuma disembunyikan di tampilan form.
        jenis_kelamin = self.usul_jenis_kelamin or (self.orang_id.jenis_kelamin if self.orang_id else False)
        vals = {}
        for usul_fname, orang_fname in USUL_MUATAN_MAP.items():
            if usul_fname in ('usul_suami_nama', 'usul_suami_marga_id') and jenis_kelamin != 'P':
                continue
            nilai = self[usul_fname]
            if not nilai:
                continue
            vals[orang_fname] = nilai.id if self._fields[usul_fname].type == 'many2one' else nilai
        # masih_hidup Boolean di tarombo.orang punya False sebagai nilai sah
        # ("sudah wafat"), jadi tidak bisa dipetakan generik lewat "if not nilai:
        # continue" seperti field lain (nanti "Tidak" malah dianggap belum diisi).
        # usul_masih_hidup karena itu dibuat Selection tri-state (kosong/ya/tidak).
        if self.usul_masih_hidup:
            vals['masih_hidup'] = self.usul_masih_hidup == 'ya'
        return vals

    @api.onchange('usul_desa_id')
    def _onchange_usul_desa_id(self):
        if self.usul_desa_id:
            self.usul_kecamatan_id = self.usul_desa_id.induk_id
            self.usul_kabupaten_id = self.usul_desa_id.induk_id.induk_id
            self.usul_provinsi_id = self.usul_desa_id.induk_id.induk_id.induk_id

    @api.onchange('usul_provinsi_id')
    def _onchange_usul_provinsi_id(self):
        if self.usul_kabupaten_id and self.usul_kabupaten_id.induk_id != self.usul_provinsi_id:
            self.usul_kabupaten_id = False
        if self.usul_kecamatan_id and (
                not self.usul_kabupaten_id or self.usul_kecamatan_id.induk_id != self.usul_kabupaten_id):
            self.usul_kecamatan_id = False
        if self.usul_desa_id and (
                not self.usul_kecamatan_id or self.usul_desa_id.induk_id != self.usul_kecamatan_id):
            self.usul_desa_id = False

    @api.onchange('usul_kabupaten_id')
    def _onchange_usul_kabupaten_id(self):
        if self.usul_kecamatan_id and self.usul_kecamatan_id.induk_id != self.usul_kabupaten_id:
            self.usul_kecamatan_id = False
        if self.usul_desa_id and (
                not self.usul_kecamatan_id or self.usul_desa_id.induk_id != self.usul_kecamatan_id):
            self.usul_desa_id = False

    @api.onchange('usul_kecamatan_id')
    def _onchange_usul_kecamatan_id(self):
        if self.usul_desa_id and self.usul_desa_id.induk_id != self.usul_kecamatan_id:
            self.usul_desa_id = False

    @api.constrains('ayah_id')
    def _cek_ayah_laki(self):
        for r in self:
            if r.ayah_id and r.ayah_id.jenis_kelamin != 'L':
                raise ValidationError(_(
                    'Ayah yang dipilih harus laki-laki; anak perempuan tidak melanjutkan '
                    'cabang tarombo.'
                ))

    def _cek_urutan_bentrok(self):
        self.ensure_one()
        if not self.usul_urutan:
            return
        if self.jenis == 'tambah':
            induk = self.ayah_id
            kecuali = self.env['tarombo.orang']
        else:
            induk = self.orang_id.ayah_id
            kecuali = self.orang_id
        if not induk:
            return
        saudara = self.env['tarombo.orang'].search([('ayah_id', '=', induk.id)]) - kecuali
        if self.usul_urutan in saudara.mapped('urutan'):
            raise UserError(_(
                'Nomor urut %(urutan)s sudah dipakai saudara lain. Nomor urut menentukan '
                'kedudukan haha (kakak) dan anggi (adik) antar saudara, jadi tidak boleh '
                'bentrok.', urutan=self.usul_urutan,
            ))

    def _cek_kelengkapan(self):
        self.ensure_one()
        jenis_label = dict(self._fields['jenis'].selection).get(self.jenis)
        if self.jenis == 'tambah':
            if not self.ayah_id:
                raise UserError(_('Usulan penambahan wajib mengisi Ayah.'))
            if not self.usul_nama:
                raise UserError(_('Usulan penambahan wajib mengisi nama.'))
            if not self.usul_jenis_kelamin:
                raise UserError(_('Usulan penambahan wajib mengisi jenis kelamin.'))
        else:
            if not self.orang_id:
                raise UserError(_('Usulan %s wajib memilih orang sasaran.') % jenis_label)
            if not self._muatan():
                raise UserError(_('Usulan %s tidak berisi perubahan apa pun.') % jenis_label)

    def action_ajukan(self):
        for r in self:
            r._cek_kelengkapan()
            r._cek_urutan_bentrok()
            r.write({
                'state': 'diajukan',
                'tanggal_ajukan': fields.Datetime.now(),
            })

    def action_setujui(self):
        for r in self:
            r._cek_urutan_bentrok()
            vals = r._muatan()
            if r.jenis == 'tambah':
                vals.update({
                    'ayah_id': r.ayah_id.id,
                    'marga_id': r.ayah_id.marga_id.id,
                    'punguan_id': r.punguan_id.id,
                })
                if r.pernikahan_id:
                    vals['pernikahan_id'] = r.pernikahan_id.id
                orang = self.env['tarombo.orang'].create(vals)
            else:
                orang = r.orang_id
                if vals:
                    orang.write(vals)
            r.write({
                'state': 'disetujui',
                'peninjau_id': self.env.user.id,
                'tanggal_tinjau': fields.Datetime.now(),
                'orang_hasil_id': orang.id,
            })
            # Jejak asal-usul disimpan di chatter orang itu sendiri, bukan cuma di
            # tabel usulan yang bisa saja diarsipkan/dihapus di kemudian hari.
            orang.message_post(body=r._pesan_asal_usulan())

    def action_tolak(self):
        for r in self:
            if not r.alasan_tolak:
                raise UserError(_('Alasan penolakan wajib diisi sebelum menolak usulan.'))
            r.write({
                'state': 'ditolak',
                'active': False,
                'peninjau_id': self.env.user.id,
                'tanggal_tinjau': fields.Datetime.now(),
            })

    def _pesan_asal_usulan(self):
        self.ensure_one()
        jenis_label = dict(self._fields['jenis'].selection).get(self.jenis)
        return _(
            'Data ini berasal dari usulan %(name)s (%(jenis)s) oleh %(pengusul)s. '
            'Sumber keterangan: %(sumber)s.',
            name=self.name, jenis=jenis_label, pengusul=self.pengusul_id.name,
            sumber=self.sumber_ket,
        )