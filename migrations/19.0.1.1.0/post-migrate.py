"""Backfill tanggal_lahir/tanggal_wafat (Date, baru) dari tahun_lahir/
tahun_wafat (Integer, lama) di tarombo.orang.

Field lama SUDAH DIHAPUS dari model Python, tapi kolomnya sendiri tidak
pernah otomatis di-drop Odoo dari database — jadi datanya masih aman di
sana sampai migrasi ini menyalinnya. Konvensi: kalau cuma tahun yang
diketahui (kasus umum untuk data historis), isi tanggalnya dengan 1 Januari
tahun itu (mis. 1923 -> 01-01-1923) — BUKAN berarti tanggal itu benar-benar
presisi.
"""


def migrate(cr, version):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'tarombo_orang' AND column_name IN ('tahun_lahir', 'tahun_wafat')
    """)
    kolom_lama = {r[0] for r in cr.fetchall()}

    if 'tahun_lahir' in kolom_lama:
        cr.execute("""
            UPDATE tarombo_orang
            SET tanggal_lahir = make_date(tahun_lahir, 1, 1)
            WHERE tahun_lahir IS NOT NULL AND tanggal_lahir IS NULL
        """)
    if 'tahun_wafat' in kolom_lama:
        cr.execute("""
            UPDATE tarombo_orang
            SET tanggal_wafat = make_date(tahun_wafat, 1, 1)
            WHERE tahun_wafat IS NOT NULL AND tanggal_wafat IS NULL
        """)
