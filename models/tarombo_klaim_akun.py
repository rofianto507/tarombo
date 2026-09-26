from odoo import api, fields, models, _
from odoo.exceptions import UserError

JENIS_KLAIM_SELECTION = [
    ('orang_ada', 'Orang Sudah Ada di Pohon'),
    ('orang_baru', 'Orang Belum Ada / Usul Baru'),
]

STATE_SELECTION = [
    ('draft', 'Draft'),
    ('menunggu', 'Menunggu Verifikasi'),
    ('disetujui', 'Disetujui'),
    ('ditolak', 'Ditolak'),
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
        'res.users', string='Akun Pengklaim', required=True, readonly=True,
        default=lambda self: self.env.user)
    jenis = fields.Selection(JENIS_KLAIM_SELECTION, string='Jenis', required=True)
    orang_id = fields.Many2one(
        'tarombo.orang', string='Orang yang Diklaim',
        domain="[('user_id', '=', False)]")
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

    def action_ajukan(self):
        for r in self:
            r._cek_akun_belum_tertaut()
            if r.jenis == 'orang_ada':
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
            if r.jenis == 'orang_baru':
                if r.usulan_id.state != 'disetujui':
                    raise UserError(_(
                        'Usulan penambahan orang untuk klaim ini belum disetujui. '
                        'Tinjau & setujui usulannya terlebih dahulu.'
                    ))
                if not r.orang_id:
                    r.orang_id = r.usulan_id.orang_hasil_id
            r._cek_orang_belum_diklaim(r.orang_id)
            r.orang_id.write({'user_id': r.user_id.id})
            r.write({
                'state': 'disetujui',
                'peninjau_id': self.env.user.id,
                'tanggal_tinjau': fields.Datetime.now(),
            })

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
