"""Portal Manual Book admin/pengurus.

Isi (HTML + tangkapan layar) disimpan di folder `manual/` (BUKAN `static/`),
karena berkas `static/` bisa dibuka siapa saja tanpa login. Semua dilayani lewat
rute ini dan hanya untuk pengguna login yang tergabung di grup Pengurus.
"""
import os
import re

from odoo import http
from odoo.http import Response, request
from odoo.tools import file_path

NAMA_GAMBAR = re.compile(r'^[A-Za-z0-9_-]+\.png$')
GRUP_PENGURUS = 'tarombo.group_tarombo_pengurus'


class TaromboManual(http.Controller):

    def _boleh(self):
        return request.env.user.has_group(GRUP_PENGURUS)

    def _tolak(self):
        return Response('Manual Book hanya untuk pengurus Tarombo.', status=403,
                        content_type='text/plain; charset=utf-8')

    @http.route('/tarombo/manual', type='http', auth='user', methods=['GET'])
    def halaman(self, **kw):
        if not self._boleh():
            return self._tolak()
        with open(file_path('tarombo/manual/index.html'), 'rb') as f:
            isi = f.read()
        return Response(isi, content_type='text/html; charset=utf-8', headers=[
            ('Cache-Control', 'private, no-store'),
            ('X-Robots-Tag', 'noindex, nofollow'),
        ])

    @http.route('/tarombo/manual/img/<string:nama>', type='http', auth='user', methods=['GET'])
    def gambar(self, nama, **kw):
        if not self._boleh():
            return self._tolak()
        if not NAMA_GAMBAR.match(nama):
            return request.not_found()
        try:
            jalur = file_path('tarombo/manual/img/' + nama)
        except (FileNotFoundError, ValueError):
            return request.not_found()
        if not os.path.isfile(jalur):
            return request.not_found()
        with open(jalur, 'rb') as f:
            isi = f.read()
        return Response(isi, content_type='image/png', headers=[
            ('Cache-Control', 'private, max-age=3600'),
        ])
