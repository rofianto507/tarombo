"""Visualisasi pohon penjelasan hasil Hitung Partuturan.

Menggambar dua jalur dari leluhur bersama (satu kolom bila garis lurus), lengkap
dengan sundut, urutan anak di tiap cabang, dan kesimpulan sebutan. Hasilnya
HTML + SVG murni (tanpa skrip) untuk ditampilkan di dialog Hitung Partuturan.
Semua teks dari data di-escape.
"""
from html import escape

LEBAR = 900
NODE_W = 210
NODE_H = 48
JARAK_BARIS = 86
ATAS = 16

WARNA_A = ('#2a6fb0', '#e1edf8')
WARNA_B = ('#2e7d4f', '#e3f1e8')
WARNA_ANC = ('#c8a24a', '#fbf3dc')
WARNA_TEKS = '#1d2a22'
WARNA_REDUP = '#5c6b61'
WARNA_PERHATIAN = '#b4531c'


def _pendek(teks, maks=24):
    teks = (teks or '').strip()
    return teks if len(teks) <= maks else teks[:maks - 1].rstrip() + '…'


def _node(x, y, nama, baris2, warna, tebal=False, penanda=None):
    garis, isi = warna
    kiri = x - NODE_W / 2
    out = [
        '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="10" '
        'style="fill:%s;stroke:%s;stroke-width:%s"/>' % (
            kiri, y, NODE_W, NODE_H, isi, garis, 3.5 if tebal else 2),
        '<text x="%.1f" y="%.1f" text-anchor="middle" '
        'style="font:700 13px sans-serif;fill:%s">%s</text>' % (
            x, y + 20, WARNA_TEKS, escape(_pendek(nama))),
        '<text x="%.1f" y="%.1f" text-anchor="middle" '
        'style="font:11px sans-serif;fill:%s">%s</text>' % (
            x, y + 36, WARNA_REDUP, escape(baris2)),
    ]
    if penanda:
        out.append(
            '<rect x="%.1f" y="%.1f" width="22" height="22" rx="11" style="fill:%s"/>'
            '<text x="%.1f" y="%.1f" text-anchor="middle" '
            'style="font:700 12px sans-serif;fill:#fff">%s</text>' % (
                kiri - 6, y - 8, garis, kiri + 5, y + 8, escape(penanda)))
    return ''.join(out)


def _garis(x1, y1, x2, y2, warna, kurva=False):
    if kurva:
        tengah = (y1 + y2) / 2
        d = 'M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f' % (x1, y1, x1, tengah, x2, tengah, x2, y2)
    else:
        d = 'M%.1f %.1f V%.1f' % (x1, y1, y2)
    return '<path d="%s" style="fill:none;stroke:%s;stroke-width:3"/>' % (d, warna)


def bangun_visual(orang_a, orang_b, hasil):
    """:param hasil: dict dari tarombo.orang.hitung_partuturan()."""
    anc = hasil['anc']
    if not anc:
        return (
            '<p style="color:%s">Kedua orang tidak memiliki leluhur bersama yang '
            'tercatat, sehingga pohon penjelasan tidak dapat digambar.</p>' % WARNA_REDUP)

    rantai_a = list(hasil['jalur_a'])[1:]
    rantai_b = list(hasil['jalur_b'])[1:]
    dua = bool(rantai_a) and bool(rantai_b)
    if dua:
        kolom = [(rantai_a, 235, WARNA_A, 'A'), (rantai_b, 665, WARNA_B, 'B')]
    elif rantai_a:
        kolom = [(rantai_a, LEBAR / 2, WARNA_A, 'A')]
    else:
        kolom = [(rantai_b, LEBAR / 2, WARNA_B, 'B')]

    baris = max(len(k[0]) for k in kolom) if kolom else 0
    tinggi = ATAS + (baris + 1) * JARAK_BARIS + 10
    y_anc = ATAS
    bagian = []

    # Pita sundut + label di kiri
    for i in range(baris + 1):
        y = ATAS + i * JARAK_BARIS
        if i % 2 == 0:
            bagian.append(
                '<rect x="0" y="%.1f" width="%d" height="%d" rx="8" style="fill:#eef1ee;opacity:.7"/>' % (
                    y - 8, LEBAR, NODE_H + 16))
        bagian.append(
            '<text x="10" y="%.1f" style="font:600 12px sans-serif;fill:%s">Sundut %s</text>' % (
                y + NODE_H / 2 + 4, WARNA_REDUP, (anc.sundut or 0) + i))

    # Garis dulu (di bawah kotak)
    for rantai, x, warna, _ in kolom:
        bagian.append(_garis(LEBAR / 2, y_anc + NODE_H, x, y_anc + JARAK_BARIS, warna[0], kurva=True))
        for i in range(len(rantai) - 1):
            y = ATAS + (i + 1) * JARAK_BARIS
            bagian.append(_garis(x, y + NODE_H, x, y + JARAK_BARIS, warna[0]))

    # Leluhur bersama
    baris2_anc = 'leluhur bersama'
    tanda_anc = None
    if anc.id == orang_a.id:
        tanda_anc = 'A'
    elif anc.id == orang_b.id:
        tanda_anc = 'B'
    if tanda_anc:
        baris2_anc = 'Orang %s · leluhur bersama' % tanda_anc
    if anc.ayah_id:
        baris2_anc += ' · anak ke-%s' % anc.urutan
    bagian.append(_node(
        LEBAR / 2, y_anc, anc.name, baris2_anc, WARNA_ANC,
        tebal=bool(tanda_anc), penanda=tanda_anc))

    # Kotak tiap jalur
    for rantai, x, warna, tanda in kolom:
        for i, o in enumerate(rantai):
            y = ATAS + (i + 1) * JARAK_BARIS
            akhir = i == len(rantai) - 1
            baris2 = 'anak ke-%s' % o.urutan
            if akhir:
                baris2 = 'Orang %s · %s' % (tanda, baris2)
            bagian.append(_node(x, y, o.name, baris2, warna, tebal=akhir, penanda=tanda if akhir else None))

    # Keterangan percabangan: urutan anak leluhur bersama yang menentukan tua-muda.
    # Bila baris "sundut sama" jatuh di baris yang sama dengan percabangan, kedua
    # keterangan digabung di satu tempat supaya teks tidak bertumpuk.
    if dua:
        ca, cb = rantai_a[0], rantai_b[0]
        y_tengah = ATAS + JARAK_BARIS + NODE_H / 2
        x_kiri = 235 + NODE_W / 2 + 6
        x_kanan = 665 - NODE_W / 2 - 6
        if ca.urutan != cb.urutan:
            tua, muda = (ca, cb) if ca.urutan < cb.urutan else (cb, ca)
            sisi = 'A' if tua is ca else 'B'
            baris_1 = 'ke-%s lebih tua dari ke-%s' % (tua.urutan, muda.urutan)
            baris_2 = 'cabang %s lebih tua' % sisi
        else:
            baris_1, baris_2 = 'urutan anak sama', ''

        baris_sama = None
        if hasil['jarak'] <= 1:
            baris_sama = min(len(rantai_a), len(rantai_b)) - 1
            if baris_sama < 0:
                baris_sama = None
        sundut_sama = (anc.sundut or 0) + (baris_sama or 0) + 1

        if baris_sama == 0:
            baris_2 = ('%s · sundut sama (%s)' % (baris_2, sundut_sama)) if baris_2                 else 'sundut sama (%s)' % sundut_sama
        bagian.append(
            '<path d="M%.1f %.1f H%.1f" style="stroke:%s;stroke-width:2;stroke-dasharray:6 4"/>' % (
                x_kiri, y_tengah, x_kanan, WARNA_PERHATIAN))
        bagian.append(
            '<text x="%d" y="%.1f" text-anchor="middle" '
            'style="font:700 12px sans-serif;fill:%s">%s</text>' % (
                LEBAR / 2, y_tengah - 8, WARNA_PERHATIAN, escape(baris_1)))
        if baris_2:
            bagian.append(
                '<text x="%d" y="%.1f" text-anchor="middle" '
                'style="font:11px sans-serif;fill:%s">%s</text>' % (
                    LEBAR / 2, y_tengah + 16, WARNA_REDUP, escape(baris_2)))

        # Baris sundut sama di baris lain (bukan baris percabangan)
        if baris_sama:
            y_sama = ATAS + (baris_sama + 1) * JARAK_BARIS + NODE_H / 2
            bagian.append(
                '<path d="M%.1f %.1f H%.1f" style="stroke:#c8a24a;stroke-width:2.5;'
                'stroke-dasharray:7 5"/>' % (x_kiri, y_sama, x_kanan))
            bagian.append(
                '<text x="%d" y="%.1f" text-anchor="middle" '
                'style="font:600 12px sans-serif;fill:#9a7a22">sundut sama (%s)</text>' % (
                    LEBAR / 2, y_sama - 8, sundut_sama))

    svg = (
        '<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" role="img" '
        'style="width:100%%;height:auto;display:block;background:#fff;border-radius:10px">%s</svg>'
    ) % (LEBAR, tinggi, ''.join(bagian))

    kesimpulan = (
        '<div style="margin-top:12px;padding:12px 14px;border-radius:10px;background:#e3f1e8;'
        'border:1px solid #2e7d4f;color:%(ink)s;line-height:1.55">'
        '<div><b>%(b)s</b> memanggil <b>%(a)s</b>: <b style="color:#2a6fb0">%(sa)s</b></div>'
        '<div><b>%(a)s</b> memanggil <b>%(b)s</b>: <b style="color:#2e7d4f">%(sb)s</b></div>'
        '<div style="margin-top:6px;color:%(redup)s;font-size:.92em">%(ket)s</div></div>'
    ) % {
        'ink': WARNA_TEKS, 'redup': WARNA_REDUP,
        'a': escape(orang_a.name), 'b': escape(orang_b.name),
        'sa': escape(hasil['sebutan_a'] or '-'), 'sb': escape(hasil['sebutan_b'] or '-'),
        'ket': escape(hasil['keterangan'] or ''),
    }
    legenda = (
        '<div style="margin-top:8px;font-size:.85em;color:%s">Biru: jalur ke Orang A. '
        'Hijau: jalur ke Orang B. Emas: leluhur bersama. Tua atau muda ditentukan oleh '
        'urutan anak pada titik percabangan, bukan oleh umur.</div>' % WARNA_REDUP
    )
    return '<div>%s%s%s</div>' % (svg, kesimpulan, legenda)
