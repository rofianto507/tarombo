from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

KATEGORI_MASUKAN_SELECTION = [
    ('umum', 'Masukan umum'),
    ('konten', 'Laporkan konten atau pengguna'),
    ('anak', 'Keselamatan anak'),
    ('teknis', 'Gangguan teknis'),
]

MAKS_MASUKAN_PER_JAM = 10


class TaromboMasukan(models.Model):
    _name = 'tarombo.masukan'
    _description = 'Masukan Pengguna (dari dalam aplikasi)'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(compute='_compute_name', store=True)
    user_id = fields.Many2one(
        'res.users', string='Pengirim', readonly=True, default=lambda self: self.env.user)
    kategori = fields.Selection(
        KATEGORI_MASUKAN_SELECTION, string='Kategori', required=True, index=True)
    isi = fields.Text('Isi Masukan', required=True)
    versi_app = fields.Char('Versi Aplikasi', readonly=True)
    state = fields.Selection(
        [('baru', 'Baru'), ('ditangani', 'Ditangani')],
        string='Status', default='baru', required=True, tracking=True, index=True)
    catatan_pengurus = fields.Text('Catatan Pengurus')
    penangan_id = fields.Many2one('res.users', string='Ditangani oleh', readonly=True)
    tanggal_tangani = fields.Datetime('Ditangani pada', readonly=True)

    @api.depends('kategori', 'create_date')
    def _compute_name(self):
        label = dict(KATEGORI_MASUKAN_SELECTION)
        for r in self:
            r.name = '%s — %s' % (
                label.get(r.kategori, ''), fields.Datetime.to_string(r.create_date) if r.create_date else '')

    def action_tandai_ditangani(self):
        self.write({
            'state': 'ditangani',
            'penangan_id': self.env.user.id,
            'tanggal_tangani': fields.Datetime.now(),
        })

    @api.model
    def kirim_masukan(self, kategori, isi, versi_app=False):
        """Masukan/laporan dari dalam aplikasi. Terbuka untuk setiap akun yang
        login (juga yang belum terverifikasi), supaya siapa pun dapat melapor
        tanpa keluar dari aplikasi. sudo() karena akun biasa tidak punya hak
        tulis langsung di model ini."""
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            raise AccessError(_('Silakan masuk ke akun Anda terlebih dahulu.'))
        if kategori not in dict(KATEGORI_MASUKAN_SELECTION):
            raise UserError(_('Kategori tidak dikenal.'))
        teks = (isi or '').strip()
        if len(teks) < 5:
            raise UserError(_('Isi masukan terlalu singkat.'))
        if len(teks) > 2000:
            raise UserError(_('Isi masukan maksimal 2000 karakter.'))
        Masukan = self.sudo()
        sejam = fields.Datetime.now() - timedelta(hours=1)
        if Masukan.search_count([
                ('user_id', '=', self.env.uid), ('create_date', '>=', sejam)]) >= MAKS_MASUKAN_PER_JAM:
            raise UserError(_('Terlalu banyak masukan dalam satu jam. Silakan coba lagi nanti.'))
        rec = Masukan.create({
            'user_id': self.env.uid,
            'kategori': kategori,
            'isi': teks,
            'versi_app': (versi_app or '')[:40] or False,
        })
        pengurus = self.env.ref('tarombo.group_tarombo_pengurus').sudo().all_user_ids.ids
        judul = _('Masukan: Keselamatan Anak') if kategori == 'anak' else _('Masukan Baru')
        self.env['tarombo.push_sender'].sudo().kirim(
            pengurus, judul, teks[:120],
            data={'tipe': 'masukan', 'masukan_id': rec.id, 'kategori': kategori})
        return True
