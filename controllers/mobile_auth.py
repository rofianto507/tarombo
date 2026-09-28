import re
import logging

from odoo import http
from odoo.exceptions import AccessDenied
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

    @http.route('/tarombo/mobile/google_login', type='jsonrpc', auth='public', csrf=False, cors='*')
    def google_login(self, access_token=None, **kwargs):
        """Login/registrasi otomatis via Google Sign-In native dari app mobile.

        Sengaja TIDAK memakai jalur signup otomatis bawaan auth_oauth
        (ResUsers._auth_oauth_signin() -> self.signup()), karena jalur itu
        mewajibkan auth_signup.invitation_scope='b2c' di-set GLOBAL — yang
        berarti ikut membuka form signup Odoo standar (/web/signup) untuk
        siapa saja, bukan cuma jalur mobile terkontrol ini. Sebagai gantinya,
        akun baru dibuat langsung di sini (sudo(), pola sama seperti
        register() di atas), tetap lewat validasi token yang sama persis
        dengan yang dipakai alur OAuth bawaan Odoo (provider-agnostic, HANYA
        memvalidasi access_token ke endpoint userinfo Google — reuse, bukan
        menulis ulang logika verifikasi OAuth dari nol).
        """
        if not access_token:
            return {'success': False, 'error': 'Token Google tidak ada'}

        # sudo() wajib SEBELUM baca field apa pun: auth.oauth.provider hanya
        # boleh dibaca role Administrator, sedangkan endpoint ini auth='public'
        # (dipanggil sebelum login ada). Tanpa sudo() di sini, .enabled di
        # bawah langsung AccessError untuk user publik.
        provider = request.env.ref('auth_oauth.provider_google', raise_if_not_found=False)
        if not provider:
            return {'success': False, 'error': 'Login Google belum dikonfigurasi di server.'}
        provider = provider.sudo()
        if not provider.enabled:
            return {'success': False, 'error': 'Login Google belum dikonfigurasi di server.'}

        res_users = request.env['res.users'].sudo()
        try:
            validation = res_users._auth_oauth_validate(provider.id, access_token)
        except Exception:
            _logger.info('Google login: validasi token gagal')
            return {'success': False, 'error': 'Token Google tidak valid atau kedaluwarsa.'}

        oauth_uid = validation.get('user_id')
        email = (validation.get('email') or '').strip().lower()
        name = validation.get('name') or email
        if not oauth_uid or not email:
            return {'success': False, 'error': 'Data akun Google tidak lengkap (email tidak ditemukan).'}

        # Cari akun yang sudah pernah login Google (oauth_uid sama) DULUAN;
        # kalau belum pernah, coba tautkan ke akun email/password yang sudah
        # ada (email sama) — supaya anggota yang sudah daftar manual tetap
        # bisa pakai Google tanpa jadi akun duplikat.
        user = res_users.search([('oauth_uid', '=', oauth_uid), ('oauth_provider_id', '=', provider.id)], limit=1)
        if not user:
            user = res_users.search([('login', '=', email)], limit=1)

        try:
            if user:
                user.write({
                    'oauth_provider_id': provider.id,
                    'oauth_uid': oauth_uid,
                    'oauth_access_token': access_token,
                })
            else:
                group_anggota = request.env.ref('tarombo.group_tarombo_anggota')
                user = res_users.create({
                    'name': name,
                    'login': email,
                    'email': email,
                    'oauth_provider_id': provider.id,
                    'oauth_uid': oauth_uid,
                    'oauth_access_token': access_token,
                    'group_ids': [(4, group_anggota.id)],
                })
                _logger.info('TAROMBO GOOGLE LOGIN: user baru dibuat id=%s login=%s', user.id, user.login)
            # commit supaya user baru/tertaut ini terlihat oleh authenticate()
            # di transaksi berikutnya — pola sama seperti controller
            # auth_oauth/signin bawaan Odoo (lihat addons/auth_oauth/controllers/main.py).
            request.env.cr.commit()

            credential = {'login': user.login, 'token': access_token, 'type': 'oauth_token'}
            auth_info = request.session.authenticate(request.env, credential)
            return {'success': True, 'uid': auth_info['uid']}
        except AccessDenied:
            return {'success': False, 'error': 'Login Google gagal, coba lagi.'}
        except Exception:
            _logger.exception('Google login gagal untuk %s', email)
            return {'success': False, 'error': 'Terjadi kesalahan server. Silakan coba lagi.'}

    @http.route('/tarombo/mobile/hapus_akun', type='jsonrpc', auth='user', csrf=False, cors='*')
    def hapus_akun(self, alasan=None, **kwargs):
        """Permintaan hapus akun dari app mobile — sengaja TIDAK menghapus
        res.users secara langsung (record ini kemungkinan besar terhubung ke
        tarombo.orang.user_id, tarombo.usulan sebagai pengusul, dst., jadi
        hapus langsung berisiko merusak riwayat data bersama). Sama seperti
        pola account_deletion di digital_kamtibmas: cukup catat sebagai
        permintaan yang ditindaklanjuti admin secara manual (maks. 30 hari
        kerja), konsisten dengan yang dijanjikan di halaman /hapus-akun.
        """
        user = request.env.user
        existing = request.env['tarombo.hapus_akun_request'].sudo().search([
            ('user_id', '=', user.id),
            ('state', '=', 'pending'),
        ], limit=1)
        if existing:
            return {'success': True, 'message': 'Permintaan sudah tercatat sebelumnya.'}

        request.env['tarombo.hapus_akun_request'].sudo().create({
            'nama': user.name,
            'login': user.login,
            'alasan': (alasan or '').strip() or False,
            'user_id': user.id,
        })
        return {'success': True, 'message': 'Permintaan hapus akun berhasil dikirim.'}
