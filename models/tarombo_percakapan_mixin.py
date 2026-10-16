from datetime import timedelta
from html import escape

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import html2plaintext

MAKS_PESAN = 1000
MAKS_PESAN_PER_JAM = 20


class TaromboPercakapanMixin(models.AbstractModel):
    """Percakapan dua arah antara pemilik rekaman (pengaju) dan pengurus,
    tersimpan sebagai pesan chatter biasa ("Kirim pesan") sehingga pengurus
    membalas langsung dari chatter form di panel web. Catatan internal
    ("Log note") tidak pernah tampil di aplikasi.

    Dipakai tarombo.klaim_akun dan tarombo.usulan. Model pemakai wajib
    mewarisi mail.thread, menimpa `_percakapan_pemilik()` serta atribut
    `_percakapan_*` di bawah, dan memanggil `_percakapan_beritahu_pemilik()`
    dari `message_post()` miliknya.
    """
    _name = 'tarombo.percakapan.mixin'
    _description = 'Percakapan pengaju dan pengurus (chatter)'

    # Status yang menutup percakapan (tak bisa lagi dibalas pengaju).
    _percakapan_tutup = ()
    # Nilai 'tipe' pada payload push untuk pengaju dan untuk pengurus.
    _percakapan_tipe = ''
    _percakapan_tipe_pengurus = ''
    # Nama kunci id pada payload push (kompatibel dengan aplikasi lama).
    _percakapan_kunci_id = 'record_id'

    def _percakapan_pemilik(self):
        raise NotImplementedError()

    def _percakapan_beritahu_pemilik(self, msg):
        """Balasan pengurus lewat chatter -> kabari pengaju."""
        try:
            for r in self:
                pemilik = r._percakapan_pemilik()
                if (msg.message_type == 'comment'
                        and msg.subtype_id == self.env.ref('mail.mt_comment')
                        and pemilik and msg.author_id != pemilik.partner_id):
                    self.env['tarombo.push_sender'].sudo().kirim(
                        [pemilik.id], _('Pesan dari Pengurus'),
                        html2plaintext(msg.body or '').strip()[:120],
                        data={'tipe': r._percakapan_tipe, r._percakapan_kunci_id: r.id,
                              'hasil': 'pesan'})
        except Exception:  # notifikasi tidak boleh menggagalkan pengiriman pesan
            pass

    def _domain_pesan(self):
        self.ensure_one()
        return [
            ('model', '=', self._name),
            ('res_id', '=', self.id),
            ('message_type', '=', 'comment'),
            ('subtype_id', '=', self.env.ref('mail.mt_comment').id),
        ]

    @api.model
    def _percakapan_rekaman_sendiri(self, rec_id):
        rec = self.sudo().with_context(active_test=False).browse(int(rec_id)).exists()
        if not rec or rec._percakapan_pemilik().id != self.env.uid:
            raise AccessError(_('Pengajuan tidak ditemukan.'))
        return rec

    def _percakapan(self):
        self.ensure_one()
        pesan = self.env['mail.message'].sudo().search(
            self._domain_pesan(), order='date asc, id asc')
        saya = self._percakapan_pemilik().partner_id
        return [{
            'id': m.id,
            'dari_pengurus': m.author_id != saya,
            'penulis': (m.author_id.name or _('Pengurus')) if m.author_id != saya else _('Anda'),
            'tanggal': fields.Datetime.to_string(m.date),
            'isi': html2plaintext(m.body or '').strip(),
        } for m in pesan]

    @api.model
    def get_percakapan(self, rec_id):
        """Percakapan milik pengajuan sendiri."""
        rec = self._percakapan_rekaman_sendiri(rec_id)
        return {
            'record_id': rec.id,
            # Kunci lama, dipakai aplikasi versi sebelumnya.
            'klaim_id': rec.id,
            'jenis': getattr(rec, 'jenis', False),
            'state': rec.state,
            'tutup': rec.state in rec._percakapan_tutup,
            'pesan': rec._percakapan(),
        }

    @api.model
    def kirim_pesan(self, rec_id, isi):
        """Pengaju mengirim pesan ke pengurus pada pengajuannya sendiri."""
        rec = self._percakapan_rekaman_sendiri(rec_id)
        if rec.state in rec._percakapan_tutup:
            raise UserError(_('Percakapan untuk pengajuan ini sudah ditutup.'))
        teks = (isi or '').strip()
        if not teks:
            raise UserError(_('Pesan tidak boleh kosong.'))
        if len(teks) > MAKS_PESAN:
            raise UserError(_('Pesan maksimal %d karakter.') % MAKS_PESAN)
        pemilik = rec._percakapan_pemilik()
        sejam = fields.Datetime.now() - timedelta(hours=1)
        terkirim = self.env['mail.message'].sudo().search_count(
            rec._domain_pesan() + [
                ('author_id', '=', pemilik.partner_id.id), ('date', '>=', sejam)])
        if terkirim >= MAKS_PESAN_PER_JAM:
            raise UserError(_('Terlalu banyak pesan dalam satu jam. Silakan coba lagi nanti.'))
        rec.sudo().with_context(mail_post_autofollow=False).message_post(
            body=Markup(escape(teks).replace('\n', '<br/>')),
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=pemilik.partner_id.id,
        )
        pengurus = self.env.ref('tarombo.group_tarombo_pengurus').sudo().all_user_ids.ids
        self.env['tarombo.push_sender'].sudo().kirim(
            pengurus, _('Pesan dari Pengaju'),
            _('%(nama)s: %(isi)s') % {'nama': pemilik.name, 'isi': teks[:100]},
            data={'tipe': rec._percakapan_tipe_pengurus, rec._percakapan_kunci_id: rec.id},
        )
        return rec._percakapan()
