"""Arsip: tambah tabel relasi orang_ids (banyak orang) dari orang_id lama.

Kolom orang_id dan punguan_id SENGAJA tidak dibuang: aplikasi mobile versi
lama (<= 1.0.4) masih membaca dan menulisnya. Skrip ini hanya menyalin tautan
orang_id yang ada ke relasi baru supaya arsip tetap tampil di aplikasi baru.
Kolom punguan_id kini boleh kosong (tidak lagi required di model), jadi
batasan NOT NULL lama dilepas.
"""


def migrate(cr, version):
    cr.execute("""
        INSERT INTO tarombo_arsip_orang_rel (arsip_id, orang_id)
        SELECT id, orang_id FROM tarombo_arsip WHERE orang_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)
    cr.execute("ALTER TABLE tarombo_arsip ALTER COLUMN punguan_id DROP NOT NULL")
