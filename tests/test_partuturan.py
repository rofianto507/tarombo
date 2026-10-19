from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestPartuturan(TransactionCase):
    """Pohon uji (dongan tubu, patrilineal murni):

        A (Leluhur Utama)
        |-- B1 (Anak Tua, urutan 1)
        |   |-- C1 (urutan 1)
        |   |   `-- G1 (urutan 1)
        |   |       `-- H1 (urutan 1)
        |   |-- C2 (urutan 2)
        |   |-- F1, P (urutan 3)
        |   `-- F2, P (urutan 4)
        |-- B2 (Anak Muda, urutan 2)
        |   |-- D1 (urutan 1)
        |   |-- E1 (urutan 2)
        |   `-- E2, P (urutan 3)
        `-- B3, P (Anak Perempuan, urutan 3)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.marga = cls.env['tarombo.marga'].create({'name': 'Marga Uji'})
        cls.punguan = cls.env['tarombo.punguan'].create({'name': 'Punguan Uji'})

        def buat(name, jenis_kelamin, ayah=None, urutan=1):
            vals = {
                'name': name,
                'jenis_kelamin': jenis_kelamin,
                'marga_id': cls.marga.id,
                'punguan_id': cls.punguan.id,
                'urutan': urutan,
            }
            if ayah:
                vals['ayah_id'] = ayah.id
            return cls.env['tarombo.orang'].create(vals)

        cls.A = buat('A Leluhur Utama', 'L')
        cls.B1 = buat('B1 Anak Tua', 'L', cls.A, 1)
        cls.B2 = buat('B2 Anak Muda', 'L', cls.A, 2)
        cls.B3 = buat('B3 Anak Perempuan', 'P', cls.A, 3)

        cls.C1 = buat('C1', 'L', cls.B1, 1)
        cls.C2 = buat('C2', 'L', cls.B1, 2)
        cls.F1 = buat('F1', 'P', cls.B1, 3)
        cls.F2 = buat('F2', 'P', cls.B1, 4)

        cls.D1 = buat('D1', 'L', cls.B2, 1)
        cls.E1 = buat('E1', 'L', cls.B2, 2)
        cls.E2 = buat('E2', 'P', cls.B2, 3)

        cls.G1 = buat('G1', 'L', cls.C1, 1)
        cls.H1 = buat('H1', 'L', cls.G1, 1)

        cls.Z = buat('Z Pohon Lain', 'L')  # tidak berhubungan dengan A

    def test_ayah_anak(self):
        hasil = self.A.hitung_partuturan(self.B1)
        self.assertEqual(hasil['jarak'], 1)
        self.assertTrue(hasil['senior_a'])
        self.assertEqual(hasil['sebutan_a'], 'amang')
        self.assertEqual(hasil['sebutan_b'], 'anak')

    def test_kakek_cucu(self):
        hasil = self.A.hitung_partuturan(self.C1)
        self.assertEqual(hasil['jarak'], 2)
        self.assertEqual(hasil['sebutan_a'], 'ompung')
        self.assertEqual(hasil['sebutan_b'], 'pahompu')

    def test_leluhur_jauh(self):
        hasil = self.A.hitung_partuturan(self.H1)
        self.assertEqual(hasil['jarak'], 4)
        # Tangga tiga generasi: selisih 4 dihitung seperti selisih 2.
        self.assertEqual(hasil['sebutan_a'], 'ompung')
        self.assertEqual(hasil['sebutan_b'], 'pahompu')

    def test_saudara_sekandung_haha_anggi(self):
        hasil = self.C1.hitung_partuturan(self.C2)
        self.assertEqual(hasil['jarak'], 0)
        self.assertTrue(hasil['senior_a'])
        self.assertEqual(hasil['sebutan_a'], 'haha')
        self.assertEqual(hasil['sebutan_b'], 'anggi')

    def test_angkang_anggi(self):
        hasil = self.F1.hitung_partuturan(self.F2)
        self.assertEqual(hasil['sebutan_a'], 'angkang')
        self.assertEqual(hasil['sebutan_b'], 'anggi')

    def test_ito(self):
        hasil = self.E1.hitung_partuturan(self.E2)
        self.assertEqual(hasil['sebutan_a'], 'ito')
        self.assertEqual(hasil['sebutan_b'], 'ito')

    def test_sepupu(self):
        hasil = self.C1.hitung_partuturan(self.D1)
        self.assertEqual(hasil['jarak'], 0)
        self.assertEqual(hasil['anc'], self.A)
        self.assertEqual(hasil['sebutan_a'], 'haha')
        self.assertEqual(hasil['sebutan_b'], 'anggi')

    def test_amangtua(self):
        hasil = self.B1.hitung_partuturan(self.D1)
        self.assertEqual(hasil['jarak'], 1)
        self.assertEqual(hasil['sebutan_a'], 'amangtua')
        self.assertEqual(hasil['sebutan_b'], 'anak')

    def test_amanguda(self):
        hasil = self.B2.hitung_partuturan(self.C1)
        self.assertEqual(hasil['jarak'], 1)
        self.assertEqual(hasil['sebutan_a'], 'amanguda')
        self.assertEqual(hasil['sebutan_b'], 'anak')

    def test_namboru_paraman(self):
        hasil = self.B3.hitung_partuturan(self.C1)
        self.assertEqual(hasil['jarak'], 1)
        self.assertEqual(hasil['sebutan_a'], 'namboru')
        self.assertEqual(hasil['sebutan_b'], 'paraman')

    def test_ompung_hanya_antar_lelaki(self):
        # D1 (lelaki) dan H1 (lelaki) berselisih 2 sundut tanpa garis lurus -> ompung/pahompu.
        hasil = self.D1.hitung_partuturan(self.H1)
        self.assertEqual(hasil['jarak'], 2)
        self.assertEqual(hasil['sebutan_a'], 'ompung')
        self.assertEqual(hasil['sebutan_b'], 'pahompu')

    def test_selisih_2_melibatkan_perempuan_jadi_ito(self):
        # E2 (perempuan) dan H1 (lelaki) berselisih 2 sundut -> keduanya ito.
        for x, y in ((self.E2, self.H1), (self.H1, self.E2)):
            hasil = x.hitung_partuturan(y)
            self.assertEqual(hasil['jarak'], 2)
            self.assertEqual(hasil['sebutan_a'], 'ito')
            self.assertEqual(hasil['sebutan_b'], 'ito')

    def test_selisih_3_seperti_selisih_1_amanguda(self):
        # B2 (cabang muda) dan H1 (keturunan cabang tua) berselisih 3 sundut.
        hasil = self.B2.hitung_partuturan(self.H1)
        self.assertEqual(hasil['jarak'], 3)
        self.assertEqual(hasil['sebutan_a'], 'amanguda')
        self.assertEqual(hasil['sebutan_b'], 'anak')

    def test_selisih_3_amangtua(self):
        # Kebalikannya: cabang tua (B1) dengan keturunan cabang muda berselisih 3 sundut.
        buat = lambda n, jk, ayah, u: self.env['tarombo.orang'].create({
            'name': n, 'jenis_kelamin': jk, 'marga_id': self.marga.id,
            'punguan_id': self.punguan.id, 'urutan': u, 'ayah_id': ayah.id})
        d2 = buat('D2', 'L', self.D1, 1)
        d3 = buat('D3', 'L', d2, 1)
        hasil = self.B1.hitung_partuturan(d3)
        self.assertEqual(hasil['jarak'], 3)
        self.assertEqual(hasil['sebutan_a'], 'amangtua')
        self.assertEqual(hasil['sebutan_b'], 'anak')

    def test_selisih_3_perempuan_namboru_paraman(self):
        hasil = self.B3.hitung_partuturan(self.H1)
        self.assertEqual(hasil['jarak'], 3)
        self.assertEqual(hasil['sebutan_a'], 'namboru')
        self.assertEqual(hasil['sebutan_b'], 'paraman')

    def test_selisih_3_garis_lurus_seperti_selisih_1(self):
        # Garis lurus pun mengikuti tangga tiga generasi: selisih 3 seperti selisih 1.
        hasil = self.B1.hitung_partuturan(self.H1)
        self.assertEqual(hasil['jarak'], 3)
        self.assertEqual(hasil['sebutan_a'], 'amang')
        self.assertEqual(hasil['sebutan_b'], 'anak')

    def test_selisih_4_dan_5_berulang(self):
        buat = lambda n, jk, ayah, u: self.env['tarombo.orang'].create({
            'name': n, 'jenis_kelamin': jk, 'marga_id': self.marga.id,
            'punguan_id': self.punguan.id, 'urutan': u, 'ayah_id': ayah.id})
        i1 = buat('I1', 'L', self.H1, 1)   # sundut 6
        j1 = buat('J1', 'L', i1, 1)        # sundut 7
        # A (sundut 1) - j1 (sundut 7): selisih 6, garis lurus -> seperti selisih 2
        hasil = self.A.hitung_partuturan(j1)
        self.assertEqual(hasil['jarak'], 6)
        self.assertEqual(hasil['sebutan_a'], 'ompung')
        # A - i1 (sundut 6): selisih 5, garis lurus -> seperti selisih 1
        hasil = self.A.hitung_partuturan(i1)
        self.assertEqual(hasil['jarak'], 5)
        self.assertEqual(hasil['sebutan_a'], 'amang')
        self.assertEqual(hasil['sebutan_b'], 'anak')
        # B2 (sundut 2) - i1 (sundut 6): selisih 4, percabangan lelaki -> ompung
        hasil = self.B2.hitung_partuturan(i1)
        self.assertEqual(hasil['jarak'], 4)
        self.assertEqual(hasil['sebutan_a'], 'ompung')

    def test_dua_perempuan_selisih_1_namboru_selisih_2_kakak(self):
        buat = lambda n, jk, ayah, u: self.env['tarombo.orang'].create({
            'name': n, 'jenis_kelamin': jk, 'marga_id': self.marga.id,
            'punguan_id': self.punguan.id, 'urutan': u, 'ayah_id': ayah.id})
        k1 = buat('K1', 'P', self.G1, 2)   # sundut 5, perempuan
        # F1 (perempuan, sundut 3) dan K1 (perempuan, sundut 5): selisih 2 -> angkang/anggi
        hasil = self.F1.hitung_partuturan(k1)
        self.assertEqual(hasil['jarak'], 2)
        self.assertEqual(hasil['sebutan_b'], 'anggi')    # F1 memanggil K1
        self.assertEqual(hasil['sebutan_a'], 'angkang')  # K1 memanggil F1
        # B3 (perempuan, sundut 2) dan E2 (perempuan, sundut 3): selisih 1 -> namboru/paraman
        hasil = self.B3.hitung_partuturan(self.E2)
        self.assertEqual(hasil['jarak'], 1)
        self.assertEqual(hasil['sebutan_a'], 'namboru')

    def test_diri_sendiri(self):
        hasil = self.A.hitung_partuturan(self.A)
        self.assertEqual(hasil['sebutan_a'], 'diri sendiri')
        self.assertEqual(hasil['sebutan_b'], 'diri sendiri')

    def test_tanpa_leluhur_bersama(self):
        hasil = self.A.hitung_partuturan(self.Z)
        self.assertFalse(hasil['anc'])
        self.assertEqual(hasil['sebutan_a'], 'tidak diketahui')
        self.assertEqual(hasil['sebutan_b'], 'tidak diketahui')

    def test_simetri(self):
        pasangan = [
            (self.A, self.B1),
            (self.A, self.C1),
            (self.A, self.H1),
            (self.C1, self.C2),
            (self.F1, self.F2),
            (self.E1, self.E2),
            (self.C1, self.D1),
            (self.B1, self.D1),
            (self.B2, self.C1),
            (self.B3, self.C1),
        ]
        for x, y in pasangan:
            maju = x.hitung_partuturan(y)
            mundur = y.hitung_partuturan(x)
            self.assertEqual(
                maju['sebutan_a'], mundur['sebutan_b'],
                'Simetri gagal untuk %s / %s' % (x.name, y.name))
            self.assertEqual(
                maju['sebutan_b'], mundur['sebutan_a'],
                'Simetri gagal untuk %s / %s' % (x.name, y.name))
