def post_init_hook(env):
    _seed_marga(env)
    leluhur = env['tarombo.orang'].search([('name', '=', 'Tuan Sihubil')], limit=1)
    if leluhur:
        env['ir.config_parameter'].sudo().set_param(
            'tarombo.leluhur_acuan_id', leluhur.id)


def _seed_marga(env):
    """Marga awal (Tampubolon, Baringbing, Silaen). Dulu berupa data XML
    bernoupdate, yang membuat ulang rekaman kembar setiap kali rekaman aslinya
    dihapus lalu modul di-upgrade (terjadi di server live, tempat marga sudah
    diisi lewat sinkronisasi). Kini hanya dibuat saat INSTALASI pertama dan
    hanya bila belum ada marga bernama sama."""
    Marga = env['tarombo.marga'].with_context(active_test=False)

    def ada_atau_buat(nama, induk=None):
        domain = [('name', '=', nama)]
        if induk:
            domain.append(('marga_induk_id', '=', induk.id))
        else:
            domain.append(('marga_induk_id', '=', False))
        rec = Marga.search(domain, limit=1) or Marga.search([('name', '=', nama)], limit=1)
        if rec:
            return rec
        return Marga.create({
            'name': nama, 'kelompok': 'toba',
            'marga_induk_id': induk.id if induk else False,
        })

    tampubolon = ada_atau_buat('Tampubolon')
    ada_atau_buat('Baringbing', tampubolon)
    ada_atau_buat('Silaen', tampubolon)
