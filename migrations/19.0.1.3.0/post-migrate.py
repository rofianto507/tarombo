"""Tahun lahir/wafat: isi tahun_lahir/tahun_wafat dari tanggal yang sudah ada.

tanggal_lahir/tanggal_wafat dipertahankan (aplikasi mobile lama masih
memakainya) dan tetap menjadi 1 Januari tahun itu; hanya tahunnya yang disalin.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE tarombo_orang
        SET tahun_lahir = EXTRACT(YEAR FROM tanggal_lahir)::int
        WHERE tanggal_lahir IS NOT NULL AND COALESCE(tahun_lahir, 0) = 0
    """)
    cr.execute("""
        UPDATE tarombo_orang
        SET tahun_wafat = EXTRACT(YEAR FROM tanggal_wafat)::int
        WHERE tanggal_wafat IS NOT NULL AND COALESCE(tahun_wafat, 0) = 0
    """)
    cr.execute("""
        UPDATE tarombo_usulan
        SET usul_tahun_lahir = EXTRACT(YEAR FROM usul_tanggal_lahir)::int
        WHERE usul_tanggal_lahir IS NOT NULL AND COALESCE(usul_tahun_lahir, 0) = 0
    """)
    cr.execute("""
        UPDATE tarombo_usulan
        SET usul_tahun_wafat = EXTRACT(YEAR FROM usul_tanggal_wafat)::int
        WHERE usul_tanggal_wafat IS NOT NULL AND COALESCE(usul_tahun_wafat, 0) = 0
    """)
