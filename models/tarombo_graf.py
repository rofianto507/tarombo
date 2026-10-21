from odoo import _, api, models
from odoo.exceptions import AccessError

MAKS_KEDALAMAN = 6
MAKS_SIMPUL_BAWAAN = 1500


class TaromboOrang(models.Model):
    _inherit = 'tarombo.orang'

    @api.model
    def get_graf_pohon(self, orang_id=False, kedalaman=3, dengan_leluhur=False,
                       orang_ids=False, maks_simpul=MAKS_SIMPUL_BAWAAN):
        """Simpul dan garis untuk halaman visualisasi pohon (grafik force).

        - `orang_id`: titik awal (kosong = leluhur acuan).
        - `orang_ids`: beberapa titik awal sekaligus (untuk "perluas satu tingkat");
          bila diisi, `orang_id` diabaikan dan leluhur tidak ditambahkan.
        - `kedalaman`: jumlah tingkat keturunan yang diambil dari titik awal.
        - `dengan_leluhur`: ikut sertakan rantai ayah sampai leluhur teratas.
        Jumlah simpul dibatasi `maks_simpul`; bila terpotong, `terpotong` bernilai True.
        Hanya nama, sundut, jenis kelamin, status, dan relasi ayah-anak yang dikirim.
        """
        if not self.env.user.has_group('tarombo.group_tarombo_anggota'):
            raise AccessError(_('Fitur ini khusus anggota Tarombo yang sudah login.'))
        kedalaman = max(0, min(int(kedalaman or 0), MAKS_KEDALAMAN))
        maks_simpul = max(10, min(int(maks_simpul or MAKS_SIMPUL_BAWAAN), 3000))
        Orang = self.env['tarombo.orang']

        if orang_ids:
            akar = Orang.browse([int(i) for i in orang_ids]).exists()
            dengan_leluhur = False
        elif orang_id:
            akar = Orang.browse(int(orang_id)).exists()
        else:
            akar = Orang._leluhur_acuan() or Orang.search(
                [('ayah_id', '=', False)], order='sundut, id', limit=1)
        if not akar:
            return {'akar_id': False, 'nodes': [], 'edges': [], 'terpotong': False}

        simpul = akar
        garis = []
        if dengan_leluhur:
            cur = akar[:1]
            while cur.ayah_id:
                garis.append((cur.ayah_id.id, cur.id))
                simpul |= cur.ayah_id
                cur = cur.ayah_id

        terpotong = False
        batas = akar
        for _tingkat in range(kedalaman):
            anak = Orang.search([('ayah_id', 'in', batas.ids)], order='ayah_id, urutan')
            if not anak:
                break
            sisa = maks_simpul - len(simpul)
            if len(anak) > sisa:
                anak = anak[:max(sisa, 0)]
                terpotong = True
            garis.extend((a.ayah_id.id, a.id) for a in anak)
            simpul |= anak
            batas = anak
            if terpotong or not anak:
                break

        jumlah_anak = {
            o.id: n for o, n in Orang._read_group(
                [('ayah_id', 'in', simpul.ids)], ['ayah_id'], ['__count'])
        }
        dimuat = {}
        for ayah, _anak in garis:
            dimuat[ayah] = dimuat.get(ayah, 0) + 1

        return {
            'akar_id': akar[:1].id,
            'terpotong': terpotong,
            'nodes': [{
                'id': r.id,
                'name': r.name,
                'sundut': r.sundut,
                'jk': r.jenis_kelamin,
                'status': r.status,
                'terhubung': bool(r.terhubung_akun),
                'ayah_id': r.ayah_id.id or False,
                'ayah': r.ayah_id.name or False,
                'jumlah_anak': jumlah_anak.get(r.id, 0),
                'dimuat': dimuat.get(r.id, 0),
            } for r in simpul],
            'edges': [{'source': a, 'target': b} for a, b in garis],
        }
