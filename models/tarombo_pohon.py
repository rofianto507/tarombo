from odoo import api, models

# Batas kedalaman & jumlah simpul per panggilan supaya pohon besar (ratusan
# keturunan) tidak membebani render di browser maupun query di server.
POHON_KEDALAMAN_MAKS = 4
POHON_SIMPUL_MAKS = 200


class TaromboOrang(models.Model):
    _inherit = 'tarombo.orang'

    @api.model
    def get_pohon_data(self, orang_id, mode='cabang'):
        """Struktur bersarang siap pakai untuk komponen OWL pohon silsilah.

        :param orang_id: id tarombo.orang yang jadi fokus/acuan tampilan.
        :param mode: 'cabang' (ayah + saudara tertutup + keturunan fokus) atau
            'radial' (seluruh keturunan leluhur acuan, fokus ditandai selected).
        :return: dict node {id, name, sundut, jenis_kelamin, status, punya_foto,
            selected, collapsed, has_more, children}, atau {} bila orang_id
            tidak ditemukan.
        """
        orang = self.browse(orang_id)
        if not orang.exists():
            return {}
        if mode == 'radial':
            return self._pohon_radial(orang)
        return self._pohon_cabang(orang)

    def _pohon_node_dasar(self, orang):
        return {
            'id': orang.id,
            'name': orang.name,
            'sundut': orang.sundut,
            'jenis_kelamin': orang.jenis_kelamin,
            'status': orang.status,
            # Hanya flag boolean, BUKAN data foto penuh — biar payload tetap
            # ringan untuk pohon besar. Gambar diambil langsung dari browser
            # lewat URL /web/image/ standar Odoo, bukan lewat RPC ini.
            'punya_foto': bool(orang.foto),
            'selected': False,
            'collapsed': False,
            'has_more': False,
            'children': [],
        }

    def _pohon_bangun_turun(self, orang, fokus_id, sisa_kedalaman, hitung):
        hitung['n'] += 1
        node = self._pohon_node_dasar(orang)
        node['selected'] = orang.id == fokus_id
        if sisa_kedalaman <= 0 or hitung['n'] >= POHON_SIMPUL_MAKS:
            node['has_more'] = bool(orang.anak_ids)
            return node
        node['children'] = [
            self._pohon_bangun_turun(anak, fokus_id, sisa_kedalaman - 1, hitung)
            for anak in orang.anak_ids.sorted('urutan')
        ]
        return node

    def _pohon_cabang(self, orang):
        """Mode 1: ayah, orang beserta saudara (saudara tertutup), dan keturunan orang."""
        hitung = {'n': 0}
        node_fokus = self._pohon_bangun_turun(orang, orang.id, POHON_KEDALAMAN_MAKS, hitung)

        if not orang.ayah_id:
            return node_fokus

        ayah = orang.ayah_id
        akar = self._pohon_node_dasar(ayah)
        anak_nodes = []
        for saudara in ayah.anak_ids.sorted('urutan'):
            if saudara.id == orang.id:
                anak_nodes.append(node_fokus)
                continue
            hitung['n'] += 1
            node_saudara = self._pohon_node_dasar(saudara)
            node_saudara['collapsed'] = bool(saudara.anak_ids)
            anak_nodes.append(node_saudara)
        akar['children'] = anak_nodes
        return akar

    def _pohon_radial(self, orang):
        """Mode 2: tata letak radial seluruh keturunan leluhur acuan."""
        acuan = self._leluhur_acuan()
        akar = acuan if acuan else orang
        hitung = {'n': 0}
        return self._pohon_bangun_turun(akar, orang.id, POHON_KEDALAMAN_MAKS, hitung)