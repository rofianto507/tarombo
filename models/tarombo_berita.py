from html import escape

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import html2plaintext

JENIS_BERITA_SELECTION = [
    ('berita', 'Berita'),
    ('agenda', 'Agenda'),
]

MAKS_KOMENTAR = 1000


class TaromboBerita(models.Model):
    _name = 'tarombo.berita'
    _description = 'Berita & Agenda (Tarombo)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tanggal_terbit desc, id desc'

    name = fields.Char('Judul', required=True, tracking=True)
    jenis = fields.Selection(
        JENIS_BERITA_SELECTION, string='Jenis', required=True, default='berita',
        index=True, tracking=True)
    ringkasan = fields.Text(
        'Ringkasan', help='Satu-dua kalimat untuk kartu di beranda aplikasi.')
    isi = fields.Html('Isi', sanitize=True)
    gambar = fields.Image('Gambar Sampul', max_width=1280, max_height=1280)
    state = fields.Selection(
        [('draft', 'Draft'), ('terbit', 'Terbit')], string='Status',
        default='draft', required=True, index=True, tracking=True)
    tanggal_terbit = fields.Datetime('Tanggal Terbit', readonly=True, copy=False)
    penulis_id = fields.Many2one(
        'res.users', string='Penulis', default=lambda self: self.env.user,
        readonly=True)
    # Khusus agenda
    tanggal_mulai = fields.Datetime('Mulai')
    tanggal_selesai = fields.Datetime('Selesai')
    lokasi = fields.Char('Lokasi')
    # Penentu "agenda sudah lewat": tanggal selesai bila ada, bila tidak tanggal mulai.
    akhir_efektif = fields.Datetime(
        compute='_compute_akhir_efektif', store=True, index=True)
    jumlah_komentar = fields.Integer(
        'Komentar', compute='_compute_jumlah_komentar')

    @api.depends('tanggal_mulai', 'tanggal_selesai')
    def _compute_akhir_efektif(self):
        for r in self:
            r.akhir_efektif = r.tanggal_selesai or r.tanggal_mulai

    def _domain_komentar(self):
        self.ensure_one()
        return [
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('message_type', '=', 'comment'),
            ('subtype_id', '=', self.env.ref('mail.mt_comment').id),
        ]

    def _compute_jumlah_komentar(self):
        Pesan = self.env['mail.message'].sudo()
        for r in self:
            r.jumlah_komentar = Pesan.search_count(r._domain_komentar()) if r.id else 0

    # ── alur penerbitan (panel web) ──────────────────────────────────────
    def action_terbitkan(self):
        for r in self:
            if r.jenis == 'agenda' and not r.tanggal_mulai:
                raise UserError(_('Agenda wajib punya tanggal mulai sebelum diterbitkan.'))
            r.write({'state': 'terbit', 'tanggal_terbit': fields.Datetime.now()})
            # Pemberitahuan ke anggota yang akunnya sudah tertaut. kirim() tidak
            # pernah me-raise, jadi kegagalan push tidak menggagalkan penerbitan.
            user_ids = self.env['tarombo.orang'].sudo().search(
                [('user_id', '!=', False)]).mapped('user_id').ids
            judul = _('Berita Baru') if r.jenis == 'berita' else _('Agenda Baru')
            self.env['tarombo.push_sender'].sudo().kirim(
                user_ids, judul, r.name,
                data={'tipe': 'berita', 'berita_id': r.id, 'jenis': r.jenis})

    def action_tarik(self):
        self.write({'state': 'draft'})

    # ── API aplikasi mobile ──────────────────────────────────────────────
    @api.model
    def _cek_anggota(self):
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            raise AccessError(_('Fitur ini khusus anggota Tarombo yang sudah login.'))

    def _ringkas(self):
        self.ensure_one()
        sekarang = fields.Datetime.now()
        return {
            'id': self.id,
            'judul': self.name,
            'jenis': self.jenis,
            'ringkasan': self.ringkasan or False,
            'tanggal_terbit': fields.Datetime.to_string(self.tanggal_terbit) if self.tanggal_terbit else False,
            'tanggal_mulai': fields.Datetime.to_string(self.tanggal_mulai) if self.tanggal_mulai else False,
            'tanggal_selesai': fields.Datetime.to_string(self.tanggal_selesai) if self.tanggal_selesai else False,
            'lokasi': self.lokasi or False,
            'sudah_lewat': bool(self.jenis == 'agenda' and self.akhir_efektif and self.akhir_efektif < sekarang),
            'punya_gambar': bool(self.gambar),
            'jumlah_komentar': self.jumlah_komentar,
        }

    @api.model
    def get_beranda(self, limit=5):
        """Hingga `limit` (bawaan 5) berita/agenda terbit paling baru, untuk
        slider di beranda aplikasi. Berita dan agenda digabung dalam satu
        urutan menurut tanggal terbit."""
        self._cek_anggota()
        rows = self.search([('state', '=', 'terbit')], limit=min(int(limit), 10))
        return {'items': [r._ringkas() for r in rows]}

    @api.model
    def get_daftar(self, jenis=False, offset=0, limit=20):
        """Daftar lengkap yang sudah terbit. `jenis` kosong = berita dan agenda."""
        self._cek_anggota()
        domain = [('state', '=', 'terbit')]
        if jenis:
            if jenis not in ('berita', 'agenda'):
                raise UserError(_('Jenis tidak dikenal.'))
            domain.append(('jenis', '=', jenis))
        rows = self.search(domain, offset=int(offset), limit=min(int(limit), 50))
        return [r._ringkas() for r in rows]

    def _komentar(self):
        """Komentar (lama ke baru), siap pakai untuk aplikasi."""
        self.ensure_one()
        Pesan = self.env['mail.message'].sudo()
        pesan = Pesan.search(self._domain_komentar(), order='date asc, id asc')
        Orang = self.env['tarombo.orang'].sudo()
        Users = self.env['res.users'].sudo()
        hasil = []
        for m in pesan:
            user = Users.search([('partner_id', '=', m.author_id.id)], limit=1) if m.author_id else Users
            orang = Orang.search([('user_id', '=', user.id)], limit=1) if user else Orang
            hasil.append({
                'id': m.id,
                'penulis': orang.name or m.author_id.name or _('Anggota'),
                'orang_id': orang.id or False,
                'tanggal': fields.Datetime.to_string(m.date),
                'isi': html2plaintext(m.body or '').strip(),
                'milik_sendiri': bool(user) and user.id == self.env.uid,
                'pengurus': bool(user) and user.has_group('tarombo.group_tarombo_pengurus'),
            })
        return hasil

    @api.model
    def get_detail(self, berita_id):
        self._cek_anggota()
        rec = self.search([('id', '=', int(berita_id)), ('state', '=', 'terbit')], limit=1)
        if not rec:
            raise UserError(_('Berita tidak ditemukan atau belum diterbitkan.'))
        data = rec._ringkas()
        data.update({
            'isi': rec.isi or False,
            'penulis': rec.penulis_id.name,
            'komentar': rec._komentar(),
        })
        return data

    @api.model
    def tambah_komentar(self, berita_id, isi):
        """Komentar anggota — hanya akun yang sudah tertaut ke data anggota
        (terverifikasi). Disimpan sebagai pesan chatter biasa ("Kirim pesan"),
        sehingga pengurus melihat dan membalasnya langsung di chatter form."""
        self._cek_anggota()
        orang = self.env['tarombo.orang'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if not orang and not self.env.user.has_group('tarombo.group_tarombo_pengurus'):
            raise UserError(_('Hanya akun yang sudah terverifikasi yang dapat berkomentar.'))
        teks = (isi or '').strip()
        if not teks:
            raise UserError(_('Komentar tidak boleh kosong.'))
        if len(teks) > MAKS_KOMENTAR:
            raise UserError(_('Komentar maksimal %d karakter.') % MAKS_KOMENTAR)
        rec = self.search([('id', '=', int(berita_id)), ('state', '=', 'terbit')], limit=1)
        if not rec:
            raise UserError(_('Berita tidak ditemukan atau belum diterbitkan.'))
        # Teks murni: di-escape lalu baris baru jadi <br>, supaya tidak ada HTML
        # dari pengguna yang masuk ke chatter.
        badan = Markup(escape(teks).replace('\n', '<br/>'))
        rec.sudo().with_context(mail_post_autofollow=False).message_post(
            body=badan,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=self.env.user.partner_id.id,
        )
        return rec._komentar()

    @api.model
    def hapus_komentar(self, message_id):
        """Hapus komentar milik sendiri; pengurus boleh menghapus komentar siapa pun."""
        self._cek_anggota()
        pesan = self.env['mail.message'].sudo().browse(int(message_id)).exists()
        if not pesan or pesan.model != self._name or pesan.message_type != 'comment':
            raise UserError(_('Komentar tidak ditemukan.'))
        pengurus = self.env.user.has_group('tarombo.group_tarombo_pengurus')
        if pesan.author_id != self.env.user.partner_id and not pengurus:
            raise UserError(_('Anda hanya dapat menghapus komentar milik sendiri.'))
        rec = self.sudo().browse(pesan.res_id)
        pesan.unlink()
        return rec._komentar() if rec.exists() else []
