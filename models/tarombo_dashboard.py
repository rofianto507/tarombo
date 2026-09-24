from odoo import api, models
from odoo.exceptions import AccessError

TOP_N = 8
DAFTAR_MAKS = 8


class TaromboOrang(models.Model):
    _inherit = 'tarombo.orang'

    @api.model
    def get_dashboard_data(self):
        """Data siap pakai untuk dashboard pengurus: KPI, chart, tabel, peta,
        dan arsip terbaru. Semua agregasi dilakukan di server (bukan lewat
        beberapa RPC domain terpisah seperti dashboard petadigi) supaya tetap
        satu panggilan ringan, konsisten dengan pola get_pohon_data.
        """
        if not self.env.user.has_group('tarombo.group_tarombo_pengurus'):
            raise AccessError('Dashboard ini khusus pengurus ke atas.')

        Orang = self.env['tarombo.orang']
        Usulan = self.env['tarombo.usulan']
        Punguan = self.env['tarombo.punguan']
        Marga = self.env['tarombo.marga']
        Arsip = self.env['tarombo.arsip']

        total_anggota = Orang.search_count([])
        total_sahih = Orang.search_count([('status', '=', 'sahih')])
        persen_lengkap = round(total_sahih / total_anggota * 100, 1) if total_anggota else 0.0

        return {
            'kpi': {
                'total_anggota': total_anggota,
                'persen_lengkap': persen_lengkap,
                'usulan_menunggu': Usulan.search_count([('state', '=', 'diajukan')]),
                'total_punguan': Punguan.search_count([]),
                'total_marga': Marga.search_count([]),
            },
            'jenis_kelamin': self._dashboard_jenis_kelamin(),
            'per_sundut': self._dashboard_per_sundut(),
            'per_punguan': self._dashboard_per_punguan(),
            'per_marga': self._dashboard_per_marga(),
            'tabel_punguan': self._dashboard_tabel_punguan(),
            'usulan_menunggu_list': self._dashboard_usulan_menunggu(),
            'map_points': self._dashboard_map_points(),
            'arsip_terbaru': self._dashboard_arsip_terbaru(Arsip),
        }

    def _dashboard_jenis_kelamin(self):
        label = dict(self._fields['jenis_kelamin'].selection)
        hasil = self._read_group([], ['jenis_kelamin'], ['__count'])
        return [
            {'name': label.get(jk, jk or 'Tidak diisi'), 'value': jumlah}
            for jk, jumlah in hasil
        ]

    def _dashboard_per_sundut(self):
        hasil = self._read_group([], ['sundut'], ['__count'], order='sundut asc')
        return [{'sundut': sundut, 'jumlah': jumlah} for sundut, jumlah in hasil]

    def _dashboard_per_punguan(self):
        hasil = self._read_group(
            [], ['punguan_id'], ['__count'], order='__count desc', limit=TOP_N)
        return [
            {'name': punguan.name if punguan else 'Tanpa Punguan', 'jumlah': jumlah}
            for punguan, jumlah in hasil
        ]

    def _dashboard_per_marga(self):
        hasil = self._read_group(
            [('marga_id', '!=', False)], ['marga_id'], ['__count'],
            order='__count desc', limit=TOP_N)
        return [{'name': marga.name, 'jumlah': jumlah} for marga, jumlah in hasil]

    def _dashboard_tabel_punguan(self):
        hasil = self._read_group([], ['punguan_id', 'status'], ['__count'])
        per_punguan = {}
        for punguan, status, jumlah in hasil:
            key = punguan.id if punguan else 0
            entri = per_punguan.setdefault(key, {
                'id': key,
                'name': punguan.name if punguan else 'Tanpa Punguan',
                'sahih': 0,
                'rumpang': 0,
            })
            if status == 'sahih':
                entri['sahih'] += jumlah
            else:
                entri['rumpang'] += jumlah
        baris = list(per_punguan.values())
        for b in baris:
            b['total'] = b['sahih'] + b['rumpang']
        baris.sort(key=lambda b: b['total'], reverse=True)
        return baris

    def _dashboard_usulan_menunggu(self):
        usulan = self.env['tarombo.usulan'].search(
            [('state', '=', 'diajukan')], order='tanggal_ajukan asc', limit=DAFTAR_MAKS)
        jenis_label = dict(usulan._fields['jenis'].selection)
        return [{
            'id': u.id,
            'name': u.name,
            'jenis': jenis_label.get(u.jenis, u.jenis),
            'sasaran': u.orang_id.name if u.orang_id else (u.usul_nama or '-'),
            'punguan': u.punguan_id.name,
            'tanggal_ajukan': u.tanggal_ajukan and u.tanggal_ajukan.strftime('%d-%m-%Y') or '-',
        } for u in usulan]

    def _dashboard_map_points(self):
        orang = self.env['tarombo.orang'].search(
            [('latitude', '!=', 0), ('longitude', '!=', 0)])
        return [{
            'id': o.id,
            'name': o.name,
            'lat': o.latitude,
            'lng': o.longitude,
            'sundut': o.sundut,
            'jenis_kelamin': o.jenis_kelamin,
            'status': o.status,
            'punguan': o.punguan_id.name,
            'punya_foto': bool(o.foto),
        } for o in orang]

    def _dashboard_arsip_terbaru(self, Arsip):
        arsip = Arsip.search([], order='create_date desc', limit=DAFTAR_MAKS)
        jenis_label = dict(arsip._fields['jenis'].selection)
        return [{
            'id': a.id,
            'name': a.name,
            'jenis': jenis_label.get(a.jenis, a.jenis),
            'orang': a.orang_id.name if a.orang_id else '-',
            'punya_foto': a.jenis == 'foto',
        } for a in arsip]
