from odoo import _, api, fields, models
from odoo.exceptions import UserError

ALASAN_LAPORAN_SELECTION = [
    ('spam', 'Spam atau iklan'),
    ('kasar', 'Kasar, menghina, atau melecehkan'),
    ('sara', 'Menyinggung SARA atau ujaran kebencian'),
    ('tidak_pantas', 'Konten tidak pantas atau berbahaya'),
    ('pribadi', 'Membocorkan data pribadi'),
    ('lainnya', 'Lainnya'),
]


class TaromboLaporanKonten(models.Model):
    _name = 'tarombo.laporan_konten'
    _description = 'Laporan Konten Pengguna (Komentar Berita)'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(compute='_compute_name', store=True)
    berita_id = fields.Many2one(
        'tarombo.berita', string='Berita/Agenda', ondelete='cascade', index=True)
    # id pesan chatter disimpan sebagai angka (bukan Many2one) agar laporan
    # tetap ada sebagai catatan setelah komentarnya dihapus.
    message_id = fields.Integer('ID Komentar', index=True)
    isi_komentar = fields.Text('Isi Komentar (salinan)', readonly=True)
    penulis_id = fields.Many2one('res.users', string='Penulis Komentar', readonly=True)
    pelapor_id = fields.Many2one(
        'res.users', string='Pelapor', readonly=True, default=lambda self: self.env.user)
    alasan = fields.Selection(ALASAN_LAPORAN_SELECTION, string='Alasan', required=True)
    catatan = fields.Text('Catatan Pelapor')
    state = fields.Selection(
        [('baru', 'Baru'), ('ditindak', 'Ditindak (komentar dihapus)'),
         ('diabaikan', 'Diabaikan')],
        string='Status', default='baru', required=True, tracking=True, index=True)
    peninjau_id = fields.Many2one('res.users', string='Peninjau', readonly=True)
    tanggal_tinjau = fields.Datetime('Ditinjau pada', readonly=True)

    _unik_pelapor = models.Constraint(
        'UNIQUE(message_id, pelapor_id)',
        'Anda sudah melaporkan komentar ini.',
    )

    @api.depends('berita_id.name', 'alasan')
    def _compute_name(self):
        label = dict(ALASAN_LAPORAN_SELECTION)
        for r in self:
            r.name = '%s — %s' % (r.berita_id.name or '-', label.get(r.alasan, ''))

    def _komentar_ada(self):
        self.ensure_one()
        return self.env['mail.message'].sudo().browse(self.message_id).exists()

    def action_hapus_komentar(self):
        """Tindak laporan: hapus komentarnya dan tandai semua laporan atas
        komentar yang sama sebagai ditindak."""
        for r in self:
            pesan = r._komentar_ada()
            if pesan:
                pesan.unlink()
            serupa = self.search([
                ('message_id', '=', r.message_id), ('state', '=', 'baru')])
            serupa.write({
                'state': 'ditindak',
                'peninjau_id': self.env.user.id,
                'tanggal_tinjau': fields.Datetime.now(),
            })

    def action_abaikan(self):
        self.write({
            'state': 'diabaikan',
            'peninjau_id': self.env.user.id,
            'tanggal_tinjau': fields.Datetime.now(),
        })

    def action_buka_berita(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tarombo.berita',
            'res_id': self.berita_id.id,
            'view_mode': 'form',
        }


class TaromboBerita(models.Model):
    _inherit = 'tarombo.berita'

    @api.model
    def laporkan_komentar(self, message_id, alasan, catatan=False):
        """Anggota melaporkan komentar yang dianggap melanggar aturan.
        Laporan masuk ke antrean pengurus (menu Berita & Agenda > Laporan
        Konten); pengurus mendapat notifikasi. sudo() karena anggota tidak
        punya hak tulis langsung pada model laporan."""
        self._cek_anggota()
        if alasan not in dict(ALASAN_LAPORAN_SELECTION):
            raise UserError(_('Alasan laporan tidak dikenal.'))
        pesan = self.env['mail.message'].sudo().browse(int(message_id)).exists()
        if (not pesan or pesan.model != self._name or pesan.message_type != 'comment'):
            raise UserError(_('Komentar tidak ditemukan.'))
        penulis = self.env['res.users'].sudo().search(
            [('partner_id', '=', pesan.author_id.id)], limit=1) if pesan.author_id else self.env['res.users']
        if penulis and penulis.id == self.env.uid:
            raise UserError(_('Anda tidak dapat melaporkan komentar milik sendiri.'))
        Laporan = self.env['tarombo.laporan_konten'].sudo()
        if Laporan.search_count([
                ('message_id', '=', pesan.id), ('pelapor_id', '=', self.env.uid)]):
            raise UserError(_('Anda sudah melaporkan komentar ini.'))
        from odoo.tools import html2plaintext
        laporan = Laporan.create({
            'berita_id': pesan.res_id,
            'message_id': pesan.id,
            'isi_komentar': html2plaintext(pesan.body or '').strip(),
            'penulis_id': penulis.id or False,
            'pelapor_id': self.env.uid,
            'alasan': alasan,
            'catatan': (catatan or '').strip()[:500] or False,
        })
        pengurus = self.env.ref('tarombo.group_tarombo_pengurus').sudo().all_user_ids.ids
        self.env['tarombo.push_sender'].sudo().kirim(
            pengurus, _('Komentar Dilaporkan'),
            _('Ada komentar yang dilaporkan pada "%s".') % (laporan.berita_id.name or ''),
            data={'tipe': 'laporan_konten', 'laporan_id': laporan.id},
        )
        return True
