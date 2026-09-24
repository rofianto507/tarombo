import re
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PASSWORD_MIN_LEN = 8


class TaromboMobileAuthController(http.Controller):

    @http.route('/tarombo/mobile/register', type='jsonrpc', auth='public', csrf=False, cors='*')
    def register(self, nama=None, email=None, password=None, **kwargs):
        """Registrasi mandiri (self-service) untuk app mobile — HANYA membuat
        res.users dengan grup tarombo.group_tarombo_anggota. Sengaja tidak
        mengurus apa pun soal identitas/data tarombo di sini: pencarian orang
        untuk diklaim, submit klaim, dan usulan tambah semuanya lewat call_kw
        biasa setelah login, karena ACL/ir.rule untuk itu sudah benar begitu
        akun ini jadi anggota sah.

        Sengaja TIDAK mengirim password lewat gateway apa pun (beda dari
        digital_kamtibmas yang generate password acak + kirim WhatsApp) —
        tarombo tidak punya dependensi gateway pengiriman. Pengguna memilih
        password sendiri saat daftar dan langsung login pakai kredensial itu.
        """
        nama = (nama or '').strip()
        email = (email or '').strip().lower()
        password = password or ''

        if not nama:
            return {'success': False, 'error': 'Nama wajib diisi'}
        if not email or not EMAIL_RE.match(email):
            return {'success': False, 'error': 'Email tidak valid'}
        if len(password) < PASSWORD_MIN_LEN:
            return {'success': False, 'error': 'Password minimal %d karakter' % PASSWORD_MIN_LEN}

        existing = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
        if existing:
            return {'success': False, 'error': 'Email sudah terdaftar'}

        try:
            group_anggota = request.env.ref('tarombo.group_tarombo_anggota')
            user = request.env['res.users'].sudo().create({
                'name': nama,
                'login': email,
                'email': email,
                'password': password,
                'group_ids': [(4, group_anggota.id)],
            })
            _logger.info('TAROMBO REGISTER: user created id=%s login=%s', user.id, user.login)
            return {'success': True, 'login': email}
        except Exception:
            _logger.exception('Registrasi tarombo mobile gagal untuk %s', email)
            return {'success': False, 'error': 'Terjadi kesalahan server. Silakan coba lagi.'}
