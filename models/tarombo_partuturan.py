from odoo import api, models


class TaromboOrang(models.Model):
    _inherit = 'tarombo.orang'

    @api.model
    def hitung_partuturan_mobile(self, orang_a_id, orang_b_id):
        """Bungkus hitung_partuturan() jadi JSON-serializable murni untuk
        dipanggil lewat call_kw dari app mobile — hitung_partuturan() sendiri
        mengembalikan recordset mentah (anc/jalur_a/jalur_b) yang tidak bisa
        lewat JSON-RPC apa adanya.
        """
        a = self.browse(orang_a_id)
        b = self.browse(orang_b_id)
        hasil = a.hitung_partuturan(b)
        return {
            'anc_id': hasil['anc'].id if hasil['anc'] else False,
            'anc_name': hasil['anc'].name if hasil['anc'] else False,
            'jalur_a': [{'id': o.id, 'name': o.name} for o in hasil['jalur_a']],
            'jalur_b': [{'id': o.id, 'name': o.name} for o in hasil['jalur_b']],
            'sebutan_a': hasil['sebutan_a'],
            'sebutan_b': hasil['sebutan_b'],
            'senior_a': hasil['senior_a'],
            'jarak': hasil['jarak'],
            'keterangan': hasil['keterangan'],
        }

    def leluhur_bersama(self, lain):
        """Leluhur bersama terdekat, lewat perbandingan awalan parent_path."""
        self.ensure_one()
        lain.ensure_one()
        ids_a = (self.parent_path or '').strip('/').split('/')
        ids_b = (lain.parent_path or '').strip('/').split('/')
        common = []
        for a, b in zip(ids_a, ids_b):
            if a != b:
                break
            common.append(a)
        return self.browse(int(common[-1])) if common else self.browse()

    def _istilah_leluhur(self, jarak):
        """Istilah untuk pihak yang lebih tua pada garis lurus, dipanggil oleh keturunannya."""
        if jarak == 1:
            return 'amang'
        if jarak in (2, 3):
            return 'ompung'
        return 'ompung sundut ke-%d' % jarak

    def _istilah_keturunan(self, jarak, gender_muda):
        """Istilah untuk pihak yang lebih muda pada garis lurus, dipanggil oleh leluhurnya."""
        if jarak == 1:
            return 'anak' if gender_muda == 'L' else 'boru'
        if jarak in (2, 3):
            return 'pahompu'
        return 'pahompu sundut ke-%d' % jarak

    def hitung_partuturan(self, lain):
        """Kembalikan istilah partuturan (sapaan kekerabatan Batak) antara self dan lain.

        Batasan: perhitungan ini hanya menangani dongan tubu, yaitu sesama
        keturunan patrilineal lewat garis ayah_id/parent_path. Jalur tulang
        dan hula-hula lewat garis ibu baru bisa dihitung setelah marga istri
        (tarombo.pernikahan.istri_marga_id) terisi lengkap untuk seluruh
        leluhur perempuan yang terlibat.

        :return: dict dengan kunci anc, jalur_a, jalur_b, sebutan_a,
            sebutan_b, senior_a, jarak, keterangan.
        """
        self.ensure_one()
        lain.ensure_one()

        if self.id == lain.id:
            return {
                'anc': self,
                'jalur_a': self,
                'jalur_b': self,
                'sebutan_a': 'diri sendiri',
                'sebutan_b': 'diri sendiri',
                'senior_a': False,
                'jarak': 0,
                'keterangan': '%s adalah orang yang sama.' % self.name,
            }

        anc = self.leluhur_bersama(lain)
        if not anc:
            return {
                'anc': self.browse(),
                'jalur_a': self,
                'jalur_b': lain,
                'sebutan_a': 'tidak diketahui',
                'sebutan_b': 'tidak diketahui',
                'senior_a': False,
                'jarak': abs(self.sundut - lain.sundut),
                'keterangan': (
                    '%s dan %s tidak memiliki leluhur bersama yang tercatat '
                    '(silsilah terputus atau berasal dari pohon yang berbeda).'
                ) % (self.name, lain.name),
            }

        ids_a = [int(i) for i in (self.parent_path or '').strip('/').split('/') if i]
        ids_b = [int(i) for i in (lain.parent_path or '').strip('/').split('/') if i]
        jalur_a = self.browse(ids_a[ids_a.index(anc.id):])
        jalur_b = self.browse(ids_b[ids_b.index(anc.id):])
        jarak = abs(self.sundut - lain.sundut)

        if anc.id == self.id:
            # Garis lurus: self adalah leluhur langsung lain.
            sebutan_a = self._istilah_leluhur(jarak)
            sebutan_b = self._istilah_keturunan(jarak, lain.jenis_kelamin)
            senior_a = True
            keterangan = (
                '%s adalah leluhur langsung %s, berjarak %d sundut melalui garis ayah.'
            ) % (self.name, lain.name, jarak)

        elif anc.id == lain.id:
            # Garis lurus, kebalikannya: lain adalah leluhur langsung self.
            sebutan_b = self._istilah_leluhur(jarak)
            sebutan_a = self._istilah_keturunan(jarak, self.jenis_kelamin)
            senior_a = False
            keterangan = (
                '%s adalah leluhur langsung %s, berjarak %d sundut melalui garis ayah.'
            ) % (lain.name, self.name, jarak)

        else:
            # Percabangan: cabang lebih tua ditentukan dari urutan lahir anak
            # leluhur bersama yang dilalui masing-masing jalur, BUKAN tahun lahir.
            cabang_a, cabang_b = jalur_a[1], jalur_b[1]
            a_cabang_tua = cabang_a.urutan < cabang_b.urutan

            if jarak == 0:
                senior_a = a_cabang_tua
                tua, muda = (self, lain) if a_cabang_tua else (lain, self)
                if self.jenis_kelamin == lain.jenis_kelamin == 'L':
                    istilah_tua, istilah_muda = 'haha', 'anggi'
                elif self.jenis_kelamin == lain.jenis_kelamin == 'P':
                    istilah_tua, istilah_muda = 'angkang', 'anggi'
                else:
                    istilah_tua = istilah_muda = 'ito'
                sebutan_a, sebutan_b = (
                    (istilah_tua, istilah_muda) if a_cabang_tua else (istilah_muda, istilah_tua))
                if istilah_tua == istilah_muda:
                    keterangan = (
                        '%s dan %s berada pada sundut yang sama melalui leluhur bersama %s, '
                        'namun berbeda jenis kelamin sehingga keduanya saling memanggil "ito".'
                    ) % (self.name, lain.name, anc.name)
                else:
                    keterangan = (
                        '%s dan %s berada pada sundut yang sama melalui leluhur bersama %s. '
                        'Urutan lahir anak %s menunjukkan %s (urutan %s) lebih tua dari '
                        '%s (urutan %s), sehingga %s dipanggil "%s" dan %s dipanggil "%s".'
                    ) % (
                        self.name, lain.name, anc.name, anc.name,
                        tua.name, tua.urutan, muda.name, muda.urutan,
                        tua.name, istilah_tua, muda.name, istilah_muda,
                    )

            elif jarak == 1:
                self_atas = self.sundut < lain.sundut
                atas, bawah = (self, lain) if self_atas else (lain, self)
                atas_cabang_tua = a_cabang_tua if self_atas else (not a_cabang_tua)
                induk_bawah = bawah.ayah_id
                if atas.jenis_kelamin == 'L':
                    istilah_atas = 'amangtua' if atas_cabang_tua else 'amanguda'
                    istilah_bawah = 'anak' if bawah.jenis_kelamin == 'L' else 'boru'
                    penjelas = (
                        'Sebutan %s di sini merupakan sapaan kekerabatan, bukan hubungan anak kandung.'
                    ) % istilah_bawah
                else:
                    istilah_atas = 'namboru'
                    istilah_bawah = 'bere'
                    penjelas = (
                        'Sebutan namboru/bere mengikuti garis saudara perempuan ayah, '
                        'bukan hubungan anak kandung.'
                    )
                sebutan_a, sebutan_b = (
                    (istilah_atas, istilah_bawah) if self_atas else (istilah_bawah, istilah_atas))
                senior_a = self_atas
                keterangan = (
                    '%s berada pada sundut yang sama dengan %s, yaitu ayah %s. %s'
                ) % (atas.name, induk_bawah.name, bawah.name, penjelas)

            else:
                self_atas = self.sundut < lain.sundut
                atas, bawah = (self, lain) if self_atas else (lain, self)
                istilah_atas = self._istilah_leluhur(jarak)
                istilah_bawah = self._istilah_keturunan(jarak, bawah.jenis_kelamin)
                sebutan_a, sebutan_b = (
                    (istilah_atas, istilah_bawah) if self_atas else (istilah_bawah, istilah_atas))
                senior_a = self_atas
                keterangan = (
                    '%s dan %s berselisih %d sundut melalui leluhur bersama %s tanpa hubungan '
                    'leluhur langsung (percabangan). %s memanggil %s "%s", dan sebaliknya "%s".'
                ) % (
                    self.name, lain.name, jarak, anc.name,
                    bawah.name, atas.name, istilah_atas, istilah_bawah,
                )

        return {
            'anc': anc,
            'jalur_a': jalur_a,
            'jalur_b': jalur_b,
            'sebutan_a': sebutan_a,
            'sebutan_b': sebutan_b,
            'senior_a': senior_a,
            'jarak': jarak,
            'keterangan': keterangan,
        }
