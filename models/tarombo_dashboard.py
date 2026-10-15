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
        total_terverifikasi = Orang.search_count([('status', '=', 'sahih')])
        # Terverifikasi: porsi anggota dengan status terverifikasi (bukan kelengkapan isi profil).
        persen_terverifikasi = round(total_terverifikasi / total_anggota * 100, 1) if total_anggota else 0.0

        return {
            'kpi': {
                'total_anggota': total_anggota,
                'persen_terverifikasi': persen_terverifikasi,
                'usulan_menunggu': Usulan.search_count([('state', '=', 'diajukan')]),
                'total_punguan': Punguan.search_count([]),
                'total_marga': Marga.search_count([]),
            },
            'jenis_kelamin': self._dashboard_jenis_kelamin(),
            'per_sundut': self._dashboard_per_sundut(),
            'per_pendidikan': self._dashboard_per_pendidikan(),
            'per_bidang': self._dashboard_per_bidang(),
            'tabel_domisili': self._dashboard_tabel_domisili(),
            'usulan_menunggu_list': self._dashboard_usulan_menunggu(),
            'map_points': self._dashboard_map_points(),
            'sebaran_wilayah': self._dashboard_sebaran_wilayah(),
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

    def _dashboard_per_pendidikan(self):
        """Jumlah anggota menurut pendidikan tertinggi, urut jenjang (SD -> S3),
        bukan urut jumlah. Hanya yang riwayat pendidikannya sudah tercatat —
        yang belum diisi (mayoritas data impor) tidak dimasukkan supaya tidak
        menenggelamkan batang lain."""
        label = dict(self._fields['pendidikan_tertinggi'].selection)
        urutan = list(label)
        hasil = self._read_group(
            [('pendidikan_tertinggi', '!=', False)], ['pendidikan_tertinggi'], ['__count'])
        baris = [(jenjang, jumlah) for jenjang, jumlah in hasil]
        baris.sort(key=lambda r: urutan.index(r[0]) if r[0] in urutan else len(urutan))
        return [{'name': label.get(j, j), 'jumlah': jumlah} for j, jumlah in baris]

    def _dashboard_per_bidang(self):
        """Jumlah anggota menurut bidang pekerjaan saat ini (terbanyak dulu).
        Sama seperti pendidikan: hanya yang bidangnya sudah tercatat."""
        hasil = self._read_group(
            [('bidang_kini_id', '!=', False)], ['bidang_kini_id'], ['__count'],
            order='__count desc', limit=TOP_N)
        return [{'name': bidang.name, 'jumlah': jumlah} for bidang, jumlah in hasil]

    def _dashboard_tabel_domisili(self):
        """Ringkasan anggota per kota/kabupaten, berlabel "Provinsi - Kabupaten".
        Provinsi diambil dari induk kabupaten (bukan hanya provinsi_id orang)
        karena data hasil impor kadang hanya mengisi salah satunya. Anggota
        yang belum punya domisili dikelompokkan di baris terakhir."""
        hasil = self._read_group(
            [], ['kabupaten_id', 'provinsi_id', 'status'], ['__count'])
        per_wilayah = {}
        for kabupaten, provinsi, status, jumlah in hasil:
            if kabupaten:
                prov = kabupaten.induk_id or provinsi
                key = 'k%s' % kabupaten.id
                nama = '%s - %s' % (prov.name, kabupaten.name) if prov else kabupaten.name
                urut = 0
            elif provinsi:
                key = 'p%s' % provinsi.id
                nama = '%s - (kabupaten belum diisi)' % provinsi.name
                urut = 0
            else:
                key = 'kosong'
                nama = 'Belum diisi domisili'
                urut = 1
            entri = per_wilayah.setdefault(key, {
                'id': key, 'name': nama, 'terverifikasi': 0, 'rumpang': 0, '_urut': urut,
            })
            if status == 'sahih':
                entri['terverifikasi'] += jumlah
            else:
                entri['rumpang'] += jumlah
        baris = list(per_wilayah.values())
        for b in baris:
            b['total'] = b['terverifikasi'] + b['rumpang']
        # Yang punya domisili dulu (terbanyak di atas), "belum diisi" paling bawah.
        baris.sort(key=lambda b: (b['_urut'], -b['total'], b['name']))
        for b in baris:
            del b['_urut']
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

    def _dashboard_sebaran_wilayah(self):
        """Jumlah anggota per wilayah untuk peta dashboard. Hanya tingkat
        provinsi dan kabupaten/kota: koordinat kecamatan/desa belum tersedia,
        jadi menampilkannya hanya akan menumpuk di titik kabupaten."""
        hasil = {}
        for kunci, tingkat in (('provinsi', '1'), ('kabupaten', '2')):
            data = self.get_sebaran_wilayah(tingkat)
            hasil[kunci] = [
                {
                    'id': i['id'], 'nama': i['nama'], 'nama_lengkap': i['nama_lengkap'],
                    'jumlah': i['jumlah'], 'lat': i['lat'], 'lng': i['lng'],
                }
                for i in data['items'] if i['lat'] and i['lng']
            ]
        hasil['total_anggota'] = self.search_count([])
        return hasil

    def _dashboard_map_points(self):
        # Titik lokasi rumah per orang sudah tidak dikumpulkan lagi; kunci
        # dipertahankan (kosong) agar komponen dashboard tidak error.
        return []
        orang = self.env['tarombo.orang']
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
            'orang': ', '.join(a.orang_ids.mapped('name')) if a.orang_ids else '-',
            'punya_foto': a.jenis == 'foto',
        } for a in arsip]
