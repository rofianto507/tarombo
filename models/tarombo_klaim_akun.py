from odoo import api, fields, models, _
from odoo.exceptions import UserError

JENIS_KLAIM_SELECTION = [
    ('orang_ada', 'Orang Sudah Ada di Pohon'),
    ('orang_baru', 'Orang Belum Ada / Usul Baru'),
    # Orang itu SUDAH tertaut ke akun lain, dan pengklaim menyatakan akun lama
    # itu keliru/bukan miliknya. Operator menilai; bila disetujui, tautan akun
    # lama dicabut dan orang ditautkan ke akun pengklaim.
    ('banding', 'Banding (Sudah Diklaim Akun Lain)'),
]

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('menunggu', 'Menunggu Verifikasi'),
    ('disetujui', 'Disetujui'),
    ('ditolak', 'Ditolak'),
    ('dicabut', 'Dicabut'),
    # Ditarik sendiri oleh pengaju selagi menunggu (mis. salah pilih orang).
    ('dibatalkan', 'Dibatalkan'),
]


class TaromboKlaimAkun(models.Model):
    _name = 'tarombo.klaim_akun'
    _description = 'Klaim Akun Tarombo (app mobile)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # Model terpisah dari tarombo.usulan (bukan jenis baru di sana) karena
    # "tautkan akun ke orang" bukan perubahan ISI data orang — seluruh mesin
    # USUL_MUATAN_MAP/_muatan() di usulan tidak relevan di sini, dan invarian
    # yang dibutuhkan berbeda (satu orang cuma boleh punya satu klaim aktif).

    name = fields.Char(default='Baru', readonly=True, copy=False)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users', string='Akun Pengklaim', required=True,
        default=lambda self: self.env.user,
        help='Default akun yang sedang login (alur app mobile). Pengurus boleh '
             'membuatkan klaim untuk akun lain di form backend selama masih draft; '
             'anggota biasa tetap dibatasi ir.rule (hanya klaim miliknya sendiri).')
    jenis = fields.Selection(JENIS_KLAIM_SELECTION, string='Jenis', required=True)
    orang_id = fields.Many2one(
        'tarombo.orang', string='Orang yang Diklaim')
    akun_lama_id = fields.Many2one(
        'res.users', string='Akun yang Sedang Tertaut', readonly=True,
        help='Hanya untuk banding: akun yang menautkan orang ini saat banding diajukan. '
             'Bila banding disetujui, tautan akun ini dicabut.')
    usulan_id = fields.Many2one(
        'tarombo.usulan', string='Usulan Penambahan Terkait', readonly=True,
        help='Terisi otomatis untuk jenis "Orang Belum Ada" — usulan tambah yang '
             'harus disetujui pengurus dulu sebelum klaim ini bisa disetujui.')
    catatan_pengklaim = fields.Text(
        'Alasan/Keterangan', help='Mis. "Saya anak dari X, sundut Y" — bantu pengurus verifikasi.')
    bukti_ids = fields.Many2many('ir.attachment', string='Bukti Pendukung')
    # default='draft', BUKAN 'menunggu': kalau create() langsung menandai
    # "menunggu" (sudah "disubmit" secara default), maka klaim yang create()-
    # nya sukses tapi action_ajukan()-nya GAGAL (mis. kena race guard karena
    # orang yang sama masih ada klaim lain yang menggantung) akan tetap
    # tampil sebagai "Menunggu Verifikasi" yang valid — padahal sebenarnya
    # cacat/yatim (tanggal_ajukan tetap kosong). Insiden nyata: baris begini
    # sempat jadi baris ber-id TERBARU dan membuat app mobile salah membaca
    # status akun (menampilkan klaim yatim ini, bukan klaim lain yang sudah
    # disetujui pengurus). Sekarang "menunggu" HANYA dicapai lewat
    # action_ajukan() yang benar-benar berhasil.
    state = fields.Selection(STATE_SELECTION, string='Status', default='draft', tracking=True)
    peninjau_id = fields.Many2one('res.users', string='Peninjau', readonly=True)
    tanggal_ajukan = fields.Datetime('Tanggal Diajukan', readonly=True)
    tanggal_tinjau = fields.Datetime('Tanggal Ditinjau', readonly=True)
    alasan_tolak = fields.Text('Alasan Penolakan')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('tarombo.klaim_akun') or 'Baru'
        return super().create(vals_list)

    def _cek_orang_belum_diklaim(self, orang):
        """Cek ulang di server (bukan cuma andalkan domain picker di form) —
        cegah race condition dua user klaim orang yang sama sebelum salah satu
        disetujui pengurus."""
        if orang.user_id:
            raise UserError(_('Orang ini sudah punya akun terhubung.'))
        klaim_lain = self.search([
            ('orang_id', '=', orang.id),
            ('state', '=', 'menunggu'),
            ('id', '!=', self.id if self.id else 0),
        ], limit=1)
        if klaim_lain:
            raise UserError(_(
                'Orang ini sedang menunggu verifikasi klaim dari pengguna lain. '
                'Hubungi pengurus kalau menurut Anda ini keliru.'
            ))

    def _cek_akun_belum_tertaut(self):
        """Satu akun cuma boleh tertaut ke SATU orang. Tanpa cek ini, akun yang
        klaimnya sudah disetujui (tertaut ke orang A) tetap bisa berhasil
        create()+action_ajukan() klaim baru ke orang B lain — karena
        _cek_orang_belum_diklaim() cuma memeriksa sisi ORANG (apakah orang B
        sudah dipakai), bukan sisi AKUN (apakah akun ini sudah dipakai)."""
        self.ensure_one()
        sudah = self.env['tarombo.orang'].sudo().search([('user_id', '=', self.user_id.id)], limit=1)
        if sudah and sudah.id != self.orang_id.id:
            raise UserError(_(
                'Akun ini sudah tertaut ke %(nama)s. Satu akun hanya boleh terhubung ke satu orang.',
                nama=sudah.name,
            ))

    def _cek_tidak_ada_pengajuan_lain(self):
        """Satu akun hanya boleh punya SATU pengajuan menunggu (klaim, banding,
        atau orang baru). Tanpa ini akun bisa menumpuk beberapa pengajuan ke
        orang berbeda dan membingungkan pengurus."""
        self.ensure_one()
        lain = self.sudo().search([
            ('user_id', '=', self.user_id.id),
            ('state', '=', 'menunggu'),
            ('id', '!=', self.id),
        ], limit=1)
        if lain:
            raise UserError(_(
                'Anda masih punya pengajuan yang sedang diperiksa pengurus. '
                'Tunggu hasilnya atau batalkan pengajuan itu terlebih dahulu.'))

    def action_batalkan(self):
        """Pengaju menarik sendiri pengajuannya yang masih menunggu. sudo()
        dipakai karena anggota tidak punya hak tulis di model ini; pemeriksaan
        pemilik dilakukan di sini."""
        for r in self:
            pengurus = self.env.user.has_group('tarombo.group_tarombo_pengurus')
            if r.user_id != self.env.user and not pengurus:
                raise UserError(_('Anda hanya dapat membatalkan pengajuan milik sendiri.'))
            if r.state != 'menunggu':
                raise UserError(_('Hanya pengajuan yang masih menunggu yang dapat dibatalkan.'))
            if r.jenis == 'orang_baru' and r.usulan_id and r.usulan_id.state == 'diajukan':
                # Usulan orang baru ikut ditarik dari antrean pengurus.
                r.usulan_id.sudo().write({'state': 'draft'})
            r.sudo().write({'state': 'dibatalkan', 'active': False})
            r.sudo().message_post(body=_('Pengajuan dibatalkan oleh %s.') % self.env.user.name)

    def _siapkan_banding(self):
        """Validasi pengajuan banding. Berbeda dari klaim biasa: orang yang
        dituju memang SUDAH punya akun, jadi _cek_orang_belum_diklaim() tidak
        dipakai; sebagai gantinya alasan wajib dan pengajuan ganda dicegah."""
        self.ensure_one()
        if not self.orang_id:
            raise UserError(_('Pilih orang yang dibanding terlebih dahulu.'))
        akun_lama = self.orang_id.sudo().user_id
        if not akun_lama:
            raise UserError(_(
                'Orang ini belum diklaim akun mana pun. Ajukan klaim identitas biasa saja.'))
        if akun_lama == self.user_id:
            raise UserError(_('Orang ini sudah tertaut ke akun Anda.'))
        if not (self.catatan_pengklaim or '').strip():
            raise UserError(_(
                'Alasan banding wajib diisi, mis. siapa Anda dan mengapa akun lain keliru.'))
        ganda = self.sudo().search([
            ('jenis', '=', 'banding'), ('state', '=', 'menunggu'),
            ('orang_id', '=', self.orang_id.id), ('user_id', '=', self.user_id.id),
            ('id', '!=', self.id)], limit=1)
        if ganda:
            raise UserError(_('Banding Anda untuk orang ini masih menunggu verifikasi.'))
        self.sudo().akun_lama_id = akun_lama

    def _setujui_banding(self):
        """Banding disetujui: cabut tautan akun lama, tautkan akun pengklaim.
        Dilakukan dalam satu transaksi agar tidak pernah ada dua akun tertaut ke
        orang yang sama atau orang tanpa akun di tengah proses."""
        self.ensure_one()
        if not self.orang_id:
            raise UserError(_('Orang yang dibanding belum dipilih.'))
        orang = self.orang_id
        akun_lama = orang.user_id
        Klaim = self.env['tarombo.klaim_akun'].sudo().with_context(active_test=False)
        if akun_lama and akun_lama != self.user_id:
            Klaim.search([
                ('orang_id', '=', orang.id),
                ('user_id', '=', akun_lama.id),
                ('state', '=', 'disetujui'),
            ]).write({
                'state': 'dicabut',
                'peninjau_id': self.env.user.id,
                'tanggal_tinjau': fields.Datetime.now(),
            })
            orang.write({'user_id': False})
            orang.message_post(body=_(
                'Akun terhubung (%(lama)s) dicabut karena banding %(baru)s disetujui oleh %(op)s.',
                lama=akun_lama.name, baru=self.user_id.name, op=self.env.user.name))
            self.env['tarombo.push_sender'].sudo().kirim(
                [akun_lama.id], _('Tautan Akun Dicabut'),
                _('Tautan akun Anda ke "%s" dicabut karena ada banding yang disetujui pengurus.') % orang.name,
                data={'tipe': 'klaim_akun', 'hasil': 'dicabut'},
            )
        orang.write({'user_id': self.user_id.id, 'masih_hidup': True})
        self.write({
            'state': 'disetujui',
            'peninjau_id': self.env.user.id,
            'tanggal_tinjau': fields.Datetime.now(),
        })
        self.env['tarombo.push_sender'].sudo().kirim(
            [self.user_id.id], _('Banding Disetujui'),
            _('Banding Anda disetujui. Identitas Anda sebagai "%s" sudah terhubung.') % orang.name,
            data={'tipe': 'klaim_akun', 'klaim_id': self.id, 'hasil': 'disetujui'},
        )

    def action_ajukan(self):
        for r in self:
            r._cek_akun_belum_tertaut()
            r._cek_tidak_ada_pengajuan_lain()
            if r.jenis == 'banding':
                r._siapkan_banding()
            elif r.jenis == 'orang_ada':
                if not r.orang_id:
                    raise UserError(_('Pilih orang yang diklaim terlebih dahulu.'))
                r._cek_orang_belum_diklaim(r.orang_id)
            else:
                if not r.usulan_id:
                    raise UserError(_('Usulan penambahan orang baru belum diisi.'))
                if r.usulan_id.state == 'draft':
                    r.usulan_id.action_ajukan()
            # sudo() sengaja dipakai: anggota TIDAK punya perm_write sama sekali
            # di model ini (lihat ir.model.access.csv) supaya klaim yang sudah
            # disubmit tidak bisa diedit ulang — tapi submit itu sendiri butuh
            # satu write sistem (state + tanggal_ajukan) yang dipicu pemilik
            # klaim. Pola sama seperti orang_id.sudo().write() di action_setujui().
            r.sudo().write({'state': 'menunggu', 'tanggal_ajukan': fields.Datetime.now()})

    def action_setujui(self):
        for r in self:
            r._cek_akun_belum_tertaut()
            if r.jenis == 'banding':
                r._setujui_banding()
                continue
            if r.jenis == 'orang_baru':
                if r.usulan_id.state != 'disetujui':
                    raise UserError(_(
                        'Usulan penambahan orang untuk klaim ini belum disetujui. '
                        'Tinjau & setujui usulannya terlebih dahulu.'
                    ))
                if not r.orang_id:
                    r.orang_id = r.usulan_id.orang_hasil_id
            r._cek_orang_belum_diklaim(r.orang_id)
            # Pemilik akun yang mengklaim dirinya jelas masih hidup — data impor
            # menandai hampir semua orang "wafat" (masih_hidup kosong), dan itu
            # membuat mereka tidak muncul di Direktori Keahlian.
            r.orang_id.write({'user_id': r.user_id.id, 'masih_hidup': True})
            r.write({
                'state': 'disetujui',
                'peninjau_id': self.env.user.id,
                'tanggal_tinjau': fields.Datetime.now(),
            })
            self.env['tarombo.push_sender'].sudo().kirim(
                [r.user_id.id], _('Klaim Identitas Disetujui'),
                _('Identitas Anda sebagai "%s" sudah disetujui pengurus.') % r.orang_id.name,
                data={'tipe': 'klaim_akun', 'klaim_id': r.id, 'hasil': 'disetujui'},
            )

    def action_buka_tolak_wizard(self):
        """Tombol "Tolak" di form membuka wizard isi alasan dulu — action_tolak()
        sendiri TETAP mewajibkan alasan_tolak terisi, supaya tidak ada jalan
        menolak tanpa alasan sama sekali."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Alasan Penolakan'),
            'res_model': 'tarombo.tolak.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_tolak(self):
        for r in self:
            if not r.alasan_tolak:
                raise UserError(_('Alasan penolakan wajib diisi sebelum menolak klaim.'))
            r.write({
                'state': 'ditolak',
                'active': False,
                'peninjau_id': self.env.user.id,
                'tanggal_tinjau': fields.Datetime.now(),
            })
            self.env['tarombo.push_sender'].sudo().kirim(
                [r.user_id.id], _('Klaim Identitas Ditolak'),
                _('Klaim identitas Anda ditolak: %s') % r.alasan_tolak,
                data={'tipe': 'klaim_akun', 'klaim_id': r.id, 'hasil': 'ditolak'},
            )
