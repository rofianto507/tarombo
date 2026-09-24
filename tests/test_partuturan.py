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
        self.assertEqual(hasil['sebutan_a'], 'ompung sundut ke-4')
        self.assertEqual(hasil['sebutan_b'], 'pahompu sundut ke-4')

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

    def test_namboru_bere(self):
        hasil = self.B3.hitung_partuturan(self.C1)
        self.assertEqual(hasil['jarak'], 1)
        self.assertEqual(hasil['sebutan_a'], 'namboru')
        self.assertEqual(hasil['sebutan_b'], 'bere')

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
