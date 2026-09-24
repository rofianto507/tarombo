from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .tarombo_riwayat import JENJANG_SELECTION, BIDANG_SELECTION

STATUS_SELECTION = [
    ('sahih', 'Terverifikasi'),
    ('rumpang', 'Belum Terverifikasi'),
]

JENJANG_PERINGKAT = ['sd', 'smp', 'sma', 'd1', 'd3', 'd4', 's1', 's2', 's3']


class TaromboOrang(models.Model):
    _name = 'tarombo.orang'
    _description = 'Orang (Tarombo)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = 'ayah_id'
    _parent_store = True
    _order = 'sundut, urutan, name'
    _rec_names_search = ['name']

    # Identitas
    name = fields.Char('Nama', required=True, tracking=True)
    jenis_kelamin = fields.Selection([
        ('L', 'Laki-laki'),
        ('P', 'Perempuan'),
    ], string='Jenis Kelamin', required=True, tracking=True)
    foto = fields.Image('Foto', max_width=1024, max_height=1024)
    # marga_id TIDAK required=True di level field: leluhur puncak tanpa ayah_id
    # (mis. Tuan Sihubil) mendahului percabangan marga, jadi sah tidak bermarga.
    # Wajib diisi hanya untuk siapa pun yang punya ayah_id — lihat _cek_marga_wajib.
    marga_id = fields.Many2one('tarombo.marga', string='Marga', index=True, tracking=True)
    punguan_id = fields.Many2one('tarombo.punguan', string='Punguan', required=True, index=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Kontak', tracking=True)
    # Akun login (app mobile) yang mengklaim record ini sebagai dirinya sendiri —
    # ditautkan lewat alur tarombo.klaim_akun setelah disetujui pengurus, BUKAN
    # diisi bebas oleh pemilik akun sendiri. SENGAJA TIDAK dibatasi groups= (beda
    # dari tahun_lahir/alamat/koordinat) — field ini dipakai di domain picker
    # tarombo.klaim_akun.orang_id (`user_id = False`) yang harus bisa dievaluasi
    # anggota biasa saat mencari namanya sendiri untuk diklaim; field yang dipakai
    # di domain untuk grup lebih rendah tidak boleh dibatasi groups= (pelajaran
    # yang sama seperti masih_hidup — lihat context.md bagian keamanan).
    user_id = fields.Many2one(
        'res.users', string='Akun Terhubung', readonly=True, copy=False)
    catatan = fields.Text('Catatan')

    # Struktur pohon — ayah_id sengaja Many2one biasa (bukan related lewat
    # pernikahan): banyak entri naskah tarombo tidak punya catatan pernikahan
    # sama sekali, jadi relasi orang tua-anak harus bisa dicatat langsung.
    ayah_id = fields.Many2one(
        'tarombo.orang', string='Ayah', index=True, ondelete='restrict', tracking=True)
    parent_path = fields.Char(index=True)
    anak_ids = fields.One2many('tarombo.orang', 'ayah_id', string='Anak')
    # aggregator=None: sundut & urutan angka urutan/generasi, bukan kuantitas —
    # dijumlahkan di baris grup tidak ada artinya.
    sundut = fields.Integer(
        'Sundut', compute='_compute_sundut', store=True, index=True, aggregator=None)
    urutan = fields.Integer('Anak ke-', required=True, default=1, aggregator=None)
    urutan_putra = fields.Integer('Putra ke-', compute='_compute_urutan_putra', store=True)
    jumlah_saudara = fields.Integer('Jumlah Saudara', compute='_compute_jumlah_saudara', store=True)

    # Keabsahan — 'usulan' tidak ada di sini, usulan punya modelnya sendiri.
    status = fields.Selection(STATUS_SELECTION, string='Status', default='sahih', tracking=True)
    sumber_ket = fields.Char('Sumber Keterangan', tracking=True)
    lengkap = fields.Boolean('Lengkap', compute='_compute_lengkap', store=True)

    # Khusus perempuan
    suami_nama = fields.Char('Nama Suami')
    suami_marga_id = fields.Many2one('tarombo.marga', string='Marga Suami')

    # Data pribadi — tanggal persis hanya untuk pengurus ke atas. masih_hidup
    # sengaja TIDAK dibatasi groups (beda dari tahun_lahir/tahun_wafat):
    # status hidup/wafat dipakai sebagai filter Direktori Keahlian yang harus
    # bisa dibuka anggota biasa; membatasinya per-groups akan membuat filter
    # itu gagal dengan AccessError bagi anggota.
    tahun_lahir = fields.Integer('Tahun Lahir', groups='tarombo.group_tarombo_pengurus')
    tahun_wafat = fields.Integer('Tahun Wafat', groups='tarombo.group_tarombo_pengurus')
    masih_hidup = fields.Boolean('Masih Hidup')

    # Pernikahan — seorang leluhur bisa beristri lebih dari satu, dan tiap
    # anak perlu tahu ia lahir dari pernikahan yang mana karena jalur
    # hula-hula tiap istri berbeda.
    pernikahan_ids = fields.One2many('tarombo.pernikahan', 'suami_id', string='Istri')
    pernikahan_id = fields.Many2one(
        'tarombo.pernikahan', string='Dari istri ke-',
        domain="[('suami_id','=',ayah_id)]")
    ibu_marga_id = fields.Many2one(
        'tarombo.marga', string='Marga Ibu', related='pernikahan_id.istri_marga_id', store=True)
    ibu_nama = fields.Char('Nama Ibu', related='pernikahan_id.istri_nama', store=True)

    # Domisili — provinsi/kabupaten/kecamatan/desa memakai tarombo.wilayah
    # berjenjang. Banyak leluhur hanya diketahui sampai tingkat kabupaten,
    # karena itu domain memakai operator '=?': penyaringan diabaikan bila
    # induknya kosong, bukan malah mengunci pilihan ke set kosong.
    provinsi_id = fields.Many2one(
        'tarombo.wilayah', string='Provinsi', domain=[('tingkat', '=', '1')])
    kabupaten_id = fields.Many2one(
        'tarombo.wilayah', string='Kabupaten/Kota',
        domain="[('tingkat', '=', '2'), ('induk_id', '=?', provinsi_id)]")
    kecamatan_id = fields.Many2one(
        'tarombo.wilayah', string='Kecamatan',
        domain="[('tingkat', '=', '3'), ('induk_id', '=?', kabupaten_id)]")
    desa_id = fields.Many2one(
        'tarombo.wilayah', string='Desa/Kelurahan',
        domain="[('tingkat', '=', '4'), ('induk_id', '=?', kecamatan_id)]")
    wilayah_id = fields.Many2one(
        'tarombo.wilayah', string='Wilayah Domisili',
        compute='_compute_wilayah_id', store=True, index=True)
    domisili_lengkap = fields.Char(
        'Alamat Domisili', compute='_compute_domisili_lengkap', store=True)
    negara_id = fields.Many2one(
        'res.country', string='Negara',
        default=lambda self: self.env.ref('base.id', raise_if_not_found=False))
    alamat_catatan = fields.Char(
        'Catatan Wilayah', help='Untuk wilayah lama yang sudah dimekarkan')

    # Kolom sensitif — hanya pengurus ke atas yang boleh lihat/isi lewat ORM biasa
    # (form/list/search_read). latitude/longitude diisi lewat peta interaktif
    # (widget tarombo_geo_picker) di form, bukan diketik manual. Satu-satunya
    # pengecualian yang diizinkan: method get_lokasi_kerabat() (tarombo_lokasi_mobile.py)
    # untuk fitur peta "Kerabat Terdekat" di app mobile — HANYA untuk orang yang
    # berbagi_lokasi=True (opt-in eksplisit), lewat query sudo() yang sempit &
    # sendirian di file terpisah, bukan pelonggaran groups= di field ini sendiri.
    alamat_jalan = fields.Char('Alamat Lengkap', groups='tarombo.group_tarombo_pengurus')
    kode_pos = fields.Char('Kode Pos', groups='tarombo.group_tarombo_pengurus')
    latitude = fields.Float('Latitude', digits=(10, 7), groups='tarombo.group_tarombo_pengurus')
    longitude = fields.Float('Longitude', digits=(10, 7), groups='tarombo.group_tarombo_pengurus')
    berbagi_lokasi = fields.Boolean(
        'Bagikan Lokasi ke Kerabat', default=False,
        help='Kalau aktif, titik lokasi domisili (bukan alamat lengkap) orang ini '
             'tampil di peta "Kerabat Terdekat" pada aplikasi mobile, terlihat oleh '
             'SELURUH anggota — bukan hanya pengurus. Nonaktif secara default; '
             'anggota yang bersangkutan (lewat akun yang tertaut, lihat user_id) '
             'sendiri yang mengaktifkan.')

    # Riwayat pendidikan & pekerjaan — dasar Direktori Keahlian, dipakai
    # anggota untuk saling mencari keahlian/koneksi, bukan cuma silsilah.
    pendidikan_ids = fields.One2many('tarombo.pendidikan', 'orang_id', string='Pendidikan')
    pekerjaan_ids = fields.One2many('tarombo.pekerjaan', 'orang_id', string='Pekerjaan')
    pendidikan_tertinggi = fields.Selection(
        JENJANG_SELECTION, string='Pendidikan Tertinggi',
        compute='_compute_pendidikan_tertinggi', store=True)
    pekerjaan_kini = fields.Char(
        'Pekerjaan Saat Ini', compute='_compute_pekerjaan_kini', store=True)
    bidang_kini = fields.Selection(
        BIDANG_SELECTION, string='Bidang Saat Ini',
        compute='_compute_pekerjaan_kini', store=True, index=True)

    arsip_ids = fields.One2many('tarombo.arsip', 'orang_id', string='Arsip')

    _urutan_unik = models.Constraint(
        'UNIQUE(ayah_id, urutan)',
        'Nomor urut lahir tidak boleh berulang antar saudara.',
    )

    def _kedalaman(self):
        return len((self.parent_path or '').strip('/').split('/'))

    @api.model
    def _leluhur_acuan(self):
        ref = self.env['ir.config_parameter'].sudo().get_param(
            'tarombo.leluhur_acuan_id')
        return self.browse(int(ref)) if ref else self.browse()

    @api.depends('parent_path')
    def _compute_sundut(self):
        # Sundut dihitung relatif terhadap leluhur acuan, bukan terhadap akar
        # pohon: bila kelak Sibagot ni Pohan ditambahkan di atas Tuan Sihubil,
        # nomor sundut 1-19 tidak boleh bergeser. Leluhur di atas acuan
        # mendapat sundut 0 atau negatif ("di atas <acuan>").
        acuan = self._leluhur_acuan()
        dasar = acuan._kedalaman() if acuan else 1
        for r in self:
            r.sundut = r._kedalaman() - dasar + 1

    @api.depends('ayah_id', 'urutan', 'jenis_kelamin',
                 'ayah_id.anak_ids.urutan', 'ayah_id.anak_ids.jenis_kelamin')
    def _compute_urutan_putra(self):
        for r in self:
            if r.jenis_kelamin != 'L' or not r.ayah_id:
                r.urutan_putra = 0
                continue
            putra = r.ayah_id.anak_ids.filtered(lambda a: a.jenis_kelamin == 'L').sorted('urutan')
            r.urutan_putra = (list(putra).index(r) + 1) if r in putra else 0

    @api.depends('ayah_id.anak_ids')
    def _compute_jumlah_saudara(self):
        for r in self:
            r.jumlah_saudara = len(r.ayah_id.anak_ids) - 1 if r.ayah_id else 0

    @api.depends('status', 'sumber_ket')
    def _compute_lengkap(self):
        for r in self:
            r.lengkap = r.status == 'sahih' and bool(r.sumber_ket)

    @api.depends('desa_id', 'kecamatan_id', 'kabupaten_id', 'provinsi_id')
    def _compute_wilayah_id(self):
        for r in self:
            r.wilayah_id = r.desa_id or r.kecamatan_id or r.kabupaten_id or r.provinsi_id

    @api.depends('desa_id', 'kecamatan_id', 'kabupaten_id', 'provinsi_id',
                 'desa_id.name', 'kecamatan_id.name', 'kabupaten_id.name', 'provinsi_id.name')
    def _compute_domisili_lengkap(self):
        for r in self:
            bagian = [w.name for w in (r.desa_id, r.kecamatan_id, r.kabupaten_id, r.provinsi_id) if w]
            r.domisili_lengkap = ' - '.join(bagian) if bagian else False

    @api.onchange('masih_hidup')
    def _onchange_masih_hidup(self):
        if self.masih_hidup:
            self.tahun_wafat = False

    @api.onchange('desa_id')
    def _onchange_desa_id(self):
        if self.desa_id:
            self.kecamatan_id = self.desa_id.induk_id
            self.kabupaten_id = self.desa_id.induk_id.induk_id
            self.provinsi_id = self.desa_id.induk_id.induk_id.induk_id

    # Reset wilayah di bawahnya kalau sudah tidak konsisten dengan induk barunya.
    # Dicek dulu konsistensinya (bukan reset membabi-buta) supaya tidak bentrok
    # dengan _onchange_desa_id di atas: saat desa_id dipilih, ia mengisi
    # kecamatan/kabupaten/provinsi ke atas dalam satu onchange yang sama —
    # kalau method di bawah ini asal mereset begitu field itu berubah, isian
    # yang baru saja diisi _onchange_desa_id akan langsung terhapus lagi.
    @api.onchange('provinsi_id')
    def _onchange_provinsi_id(self):
        if self.kabupaten_id and self.kabupaten_id.induk_id != self.provinsi_id:
            self.kabupaten_id = False
        if self.kecamatan_id and (not self.kabupaten_id or self.kecamatan_id.induk_id != self.kabupaten_id):
            self.kecamatan_id = False
        if self.desa_id and (not self.kecamatan_id or self.desa_id.induk_id != self.kecamatan_id):
            self.desa_id = False

    @api.onchange('kabupaten_id')
    def _onchange_kabupaten_id(self):
        if self.kecamatan_id and self.kecamatan_id.induk_id != self.kabupaten_id:
            self.kecamatan_id = False
        if self.desa_id and (not self.kecamatan_id or self.desa_id.induk_id != self.kecamatan_id):
            self.desa_id = False

    @api.onchange('kecamatan_id')
    def _onchange_kecamatan_id(self):
        if self.desa_id and self.desa_id.induk_id != self.kecamatan_id:
            self.desa_id = False

    @api.depends('pendidikan_ids.jenjang')
    def _compute_pendidikan_tertinggi(self):
        for r in self:
            peringkat = [j for j in r.pendidikan_ids.mapped('jenjang') if j in JENJANG_PERINGKAT]
            r.pendidikan_tertinggi = max(peringkat, key=JENJANG_PERINGKAT.index) if peringkat else False

    @api.depends(
        'pekerjaan_ids.sekarang', 'pekerjaan_ids.tahun_mulai',
        'pekerjaan_ids.jabatan', 'pekerjaan_ids.instansi', 'pekerjaan_ids.bidang')
    def _compute_pekerjaan_kini(self):
        for r in self:
            kini = r.pekerjaan_ids.filtered('sekarang').sorted('tahun_mulai', reverse=True)[:1]
            if not kini:
                kini = r.pekerjaan_ids.sorted('tahun_mulai', reverse=True)[:1]
            if kini:
                r.pekerjaan_kini = (
                    '%s di %s' % (kini.jabatan, kini.instansi) if kini.instansi else kini.jabatan)
                r.bidang_kini = kini.bidang
            else:
                r.pekerjaan_kini = False
                r.bidang_kini = False

    @api.depends('name', 'sundut')
    def _compute_display_name(self):
        # Nama berulang antar sundut (mis. banyak "Partalinga"), jadi sundut
        # disertakan supaya display_name tetap membedakan orangnya.
        acuan = self._leluhur_acuan()
        for r in self:
            if r.sundut >= 1:
                r.display_name = '%s (sundut %s)' % (r.name, r.sundut)
            elif acuan:
                r.display_name = '%s (di atas %s)' % (r.name, acuan.name)
            else:
                r.display_name = r.name

    @api.constrains('ayah_id')
    def _cek_garis_perempuan(self):
        """Anak perempuan tidak melanjutkan cabang."""
        for r in self:
            if r.ayah_id and r.ayah_id.jenis_kelamin == 'P':
                raise ValidationError(_(
                    'Anak perempuan tidak melanjutkan cabang tarombo. '
                    'Keturunannya mengikuti marga suami.'
                ))

    @api.constrains('ayah_id')
    def _cek_siklus(self):
        if self._has_cycle():
            raise ValidationError(_('Seseorang tidak boleh menjadi leluhur dirinya sendiri.'))

    @api.constrains('ayah_id', 'marga_id')
    def _cek_marga_wajib(self):
        for r in self:
            if r.ayah_id and not r.marga_id:
                raise ValidationError(_(
                    'Marga wajib diisi untuk siapa pun yang punya ayah tercatat. Hanya '
                    'leluhur puncak tanpa ayah (mis. leluhur acuan) yang boleh tanpa marga.'
                ))

    @api.constrains('pernikahan_id', 'ayah_id')
    def _cek_pernikahan(self):
        for r in self:
            if r.pernikahan_id and r.pernikahan_id.suami_id != r.ayah_id:
                raise ValidationError(_(
                    'Pernikahan yang dipilih bukan milik ayah yang tercatat.'
                ))

    @api.constrains('provinsi_id', 'kabupaten_id', 'kecamatan_id', 'desa_id')
    def _cek_wilayah_domisili(self):
        for r in self:
            if r.kabupaten_id and r.provinsi_id and r.kabupaten_id.induk_id != r.provinsi_id:
                raise ValidationError(_(
                    'Kabupaten/Kota yang dipilih bukan bagian dari provinsi yang dipilih.'
                ))
            if r.kecamatan_id and r.kabupaten_id and r.kecamatan_id.induk_id != r.kabupaten_id:
                raise ValidationError(_(
                    'Kecamatan yang dipilih bukan bagian dari kabupaten/kota yang dipilih.'
                ))
            if r.desa_id and r.kecamatan_id and r.desa_id.induk_id != r.kecamatan_id:
                raise ValidationError(_(
                    'Desa/Kelurahan yang dipilih bukan bagian dari kecamatan yang dipilih.'
                ))
