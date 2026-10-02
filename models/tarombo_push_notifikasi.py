import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'


class TaromboPushToken(models.Model):
    _name = 'tarombo.push_token'
    _description = 'Token Perangkat untuk Push Notification (FCM) — App Mobile'
    _rec_name = 'token'

    user_id = fields.Many2one('res.users', string='Pengguna', required=True, index=True, ondelete='cascade')
    token = fields.Char('Token FCM', required=True, index=True)
    platform = fields.Selection([('android', 'Android'), ('ios', 'iOS')], string='Platform')

    _token_uniq = models.Constraint('UNIQUE(token)', 'Token perangkat ini sudah terdaftar.')

    @api.model
    def register_token(self, token, platform=False):
        """Daftarkan/perbarui token FCM device ini ke akun yang sedang login.
        Dipanggil mobile setelah login & tiap kali FCM memicu onTokenRefresh.

        Satu token FISIK device cuma boleh terhubung ke SATU user — kalau
        device yang sama login pakai akun lain, kepemilikan token lama
        dipindah (bukan dibiarkan dobel), supaya device itu berhenti menerima
        push untuk akun sebelumnya begitu akun baru login di situ.
        """
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            raise AccessError(_('Fitur ini khusus anggota Tarombo yang sudah login.'))
        existing = self.sudo().search([('token', '=', token)], limit=1)
        if existing:
            if existing.user_id.id != self.env.uid or (platform and existing.platform != platform):
                existing.write({'user_id': self.env.uid, 'platform': platform or existing.platform})
            return True
        self.sudo().create({'user_id': self.env.uid, 'token': token, 'platform': platform})
        return True

    @api.model
    def unregister_token(self, token):
        """Hapus token device ini — dipanggil saat logout supaya device yang
        sudah logout tidak lagi menerima push untuk akun tadi."""
        self.sudo().search([('token', '=', token), ('user_id', '=', self.env.uid)]).unlink()
        return True


class TaromboNotifikasi(models.Model):
    _name = 'tarombo.notifikasi'
    _description = 'Riwayat Notifikasi — App Mobile'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='Pengguna', required=True, index=True, ondelete='cascade')
    judul = fields.Char('Judul', required=True)
    isi = fields.Text('Isi')
    tipe = fields.Char('Tipe')
    data = fields.Char('Data Tambahan')  # JSON string, mis. {"usulan_id": 5} — dipakai mobile untuk deep link
    dibaca = fields.Boolean('Sudah Dibaca', default=False, index=True)

    @api.model
    def tandai_dibaca(self, ids):
        """Tandai sejumlah notifikasi milik akun yang login sebagai sudah
        dibaca — dibatasi ke user_id sendiri meski id dikirim dari client,
        supaya satu akun tidak bisa menandai notifikasi akun lain."""
        self.sudo().search([('id', 'in', ids), ('user_id', '=', self.env.uid)]).write({'dibaca': True})
        return True

    @api.model
    def tandai_semua_dibaca(self):
        self.sudo().search([('user_id', '=', self.env.uid), ('dibaca', '=', False)]).write({'dibaca': True})
        return True


class TaromboPushSender(models.AbstractModel):
    _name = 'tarombo.push_sender'
    _description = 'Pengirim Push Notification (FCM HTTP v1)'

    @api.model
    def _get_access_token(self):
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        sa_json = self.env['ir.config_parameter'].sudo().get_param('tarombo.fcm_service_account_json')
        if not sa_json:
            return None
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=[FCM_SCOPE])
        creds.refresh(Request())
        return creds.token

    @api.model
    def kirim(self, user_ids, judul, isi, data=None):
        """Kirim push notification ke semua device terdaftar milik user_ids.

        Tidak pernah me-raise — gagal kirim TIDAK BOLEH menggagalkan alur
        bisnis utama (approve klaim/usulan, dst) yang memanggil method ini.
        Mengembalikan ringkasan dict `{'ok': bool, 'detail': str}` supaya
        pemanggil BISA (opsional) menuliskannya ke chatter record terkait —
        pengurus jadi punya cara lihat status kirim tanpa perlu akses log
        server (lihat pemanggilan di tarombo_usulan.py/tarombo_klaim_akun.py).
        """
        import requests

        if not user_ids:
            return {'ok': False, 'detail': 'Tidak ada penerima.'}

        # Catatan di inbox dalam-app dibuat TERLEPAS dari sukses/gagalnya
        # pengiriman push fisik di bawah — badge & tab Notifikasi tetap harus
        # mencerminkan bahwa event ini terjadi, bahkan kalau FCM belum
        # dikonfigurasi atau device belum terdaftar.
        self.env['tarombo.notifikasi'].sudo().create([
            {
                'user_id': uid,
                'judul': judul,
                'isi': isi,
                'tipe': (data or {}).get('tipe'),
                'data': json.dumps(data or {}),
            }
            for uid in user_ids
        ])

        project_id = self.env['ir.config_parameter'].sudo().get_param('tarombo.fcm_project_id')
        if not project_id:
            return {'ok': False, 'detail': 'tarombo.fcm_project_id belum di-set.'}
        try:
            access_token = self._get_access_token()
        except Exception as e:
            _logger.exception('Gagal mengambil access token FCM — cek tarombo.fcm_service_account_json.')
            return {'ok': False, 'detail': f'Gagal ambil access token FCM: {e}'}
        if not access_token:
            return {'ok': False, 'detail': 'tarombo.fcm_service_account_json belum di-set.'}

        tokens = self.env['tarombo.push_token'].sudo().search([('user_id', 'in', user_ids)])
        if not tokens:
            return {'ok': False, 'detail': 'Penerima belum punya device terdaftar (belum pernah login app mobile).'}
        url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        terkirim, gagal, pesan_gagal = 0, 0, []
        for t in tokens:
            payload = {
                'message': {
                    'token': t.token,
                    'notification': {'title': judul, 'body': isi},
                    'data': {str(k): str(v) for k, v in (data or {}).items()},
                }
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                if resp.status_code < 300:
                    terkirim += 1
                elif resp.status_code == 404 or (resp.status_code == 400 and 'UNREGISTERED' in resp.text):
                    t.unlink()  # token sudah tidak valid (uninstall/reset) — bersihkan
                    gagal += 1
                    pesan_gagal.append(f'token id={t.id}: token tidak valid, dihapus')
                else:
                    gagal += 1
                    pesan_gagal.append(f'token id={t.id}: HTTP {resp.status_code} — {resp.text[:300]}')
                    _logger.warning('FCM gagal kirim ke token id=%s: %s', t.id, resp.text)
            except Exception as e:
                gagal += 1
                pesan_gagal.append(f'token id={t.id}: {e}')
                _logger.exception('Gagal kirim push ke token id=%s', t.id)
        detail = f'{terkirim} terkirim, {gagal} gagal.'
        if pesan_gagal:
            detail += ' ' + '; '.join(pesan_gagal)
        return {'ok': terkirim > 0, 'detail': detail}
