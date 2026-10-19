"""Halaman uji Hitung Partuturan (tanpa login) untuk pengurus.

Data silsilah bersifat tertutup (hanya untuk anggota terverifikasi), jadi halaman
ini DIKUNCI dengan kode akses: nilainya di parameter sistem
`tarombo.uji_partuturan_kode`. Bila parameter itu kosong, halaman nonaktif.
Hanya mengembalikan nama, sundut, ayah, dan hasil sebutan; tidak ada kontak,
alamat, atau tahun lahir. Hapus parameter itu untuk mematikan halaman.
"""
import hmac
import json
import time

from odoo import http
from odoo.http import Response, request

from ..wizard.partuturan_visual import bangun_visual

PARAM_KODE = 'tarombo.uji_partuturan_kode'
MIN_HURUF = 3
MAKS_HASIL = 15

_HALAMAN = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Uji Partuturan &ndash; Tarombo</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F5F4F0;color:#16261B;line-height:1.6;font-size:15px}
.header{background:#2E5339;padding:26px 20px;text-align:center}
.header h1{color:#fff;font-size:21px;font-weight:800}
.header p{color:rgba(255,255,255,.7);font-size:13px;margin-top:4px}
.wrap{max-width:900px;margin:0 auto;padding:20px 16px 60px}
.card{background:#fff;border:1px solid #E4E0D4;border-radius:12px;padding:16px 18px;margin-bottom:14px}
.card h2{font-size:15px;margin-bottom:8px}
.note{background:#FBF3DC;border:1px solid #E7D79A;color:#5a4a12;border-radius:10px;padding:10px 14px;font-size:13px;margin-bottom:14px}
label{display:block;font-size:13px;font-weight:600;margin:10px 0 4px}
input[type=text],input[type=password]{width:100%;padding:10px 12px;border:1px solid #D9D5C6;border-radius:8px;font-size:15px;background:#fff}
input:focus{outline:none;border-color:#2E5339;box-shadow:0 0 0 3px rgba(46,83,57,.12)}
.hasil-cari{border:1px solid #E4E0D4;border-radius:8px;margin-top:4px;max-height:260px;overflow:auto;background:#fff}
.hasil-cari button{display:block;width:100%;text-align:left;padding:9px 12px;border:0;border-bottom:1px solid #EFEDE4;background:#fff;font-size:14px;cursor:pointer}
.hasil-cari button:hover{background:#F0F5F1}
.hasil-cari .kosong{padding:9px 12px;color:#777;font-size:13px}
.dipilih{margin-top:6px;padding:8px 12px;border-radius:8px;background:#E6EFE8;font-size:14px;display:none}
.baris{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.btn{border:0;border-radius:8px;padding:11px 18px;font-size:15px;font-weight:700;cursor:pointer}
.btn-utama{background:#2E5339;color:#fff}
.btn-sekunder{background:#E8E5DA;color:#2E5339}
.btn:disabled{opacity:.5;cursor:default}
.galat{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;border-radius:8px;padding:10px 12px;margin-top:12px;display:none;font-size:14px}
#hasil{display:none}
.sebutan{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.sebutan div{background:#2E5339;color:#fff;border-radius:10px;padding:12px;text-align:center}
.sebutan small{display:block;opacity:.75;font-size:12px}
.sebutan b{display:block;font-size:20px;color:#E8C873;margin-top:2px}
@media(max-width:560px){.sebutan{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="header"><h1>Uji Hitung Partuturan</h1><p>Halaman pengujian untuk pengurus</p></div>
<div class="wrap">
  <div class="note">Halaman ini hanya untuk menguji aturan penyebutan. Data silsilah bersifat tertutup,
  jadi diperlukan kode akses dari pengelola. Jangan dibagikan ke pihak luar.</div>
  <div class="card">
    <label for="kode">Kode akses</label>
    <input type="password" id="kode" autocomplete="off" placeholder="Masukkan kode akses">

    <label for="qa">Orang A</label>
    <input type="text" id="qa" autocomplete="off" placeholder="Ketik minimal 3 huruf nama">
    <div id="ra" class="hasil-cari" style="display:none"></div>
    <div id="da" class="dipilih"></div>

    <label for="qb">Orang B</label>
    <input type="text" id="qb" autocomplete="off" placeholder="Ketik minimal 3 huruf nama">
    <div id="rb" class="hasil-cari" style="display:none"></div>
    <div id="db" class="dipilih"></div>

    <div class="baris">
      <button class="btn btn-utama" id="hitung" disabled>Hitung Partuturan</button>
      <button class="btn btn-sekunder" id="tukar" type="button">Tukar A dan B</button>
    </div>
    <div class="galat" id="galat"></div>
  </div>

  <div class="card" id="hasil">
    <h2>Hasil</h2>
    <div class="sebutan">
      <div><small id="la"></small><b id="sa"></b></div>
      <div><small id="lb"></small><b id="sb"></b></div>
    </div>
    <div id="visual"></div>
  </div>
</div>
<script>
(function(){
  var terpilih={a:null,b:null}, timer={};
  function el(i){return document.getElementById(i)}
  function galat(t){var g=el('galat');g.textContent=t||'';g.style.display=t?'block':'none'}
  try{var k=sessionStorage.getItem('uji_kode');if(k)el('kode').value=k}catch(e){}
  el('kode').addEventListener('input',function(){try{sessionStorage.setItem('uji_kode',el('kode').value)}catch(e){}});

  function tampilDipilih(s){
    var o=terpilih[s],d=el('d'+s);
    if(!o){d.style.display='none';return}
    d.textContent='Dipilih: '+o.label;d.style.display='block';
  }
  function perbarui(){el('hitung').disabled=!(terpilih.a&&terpilih.b)}

  function cari(s){
    var q=el('q'+s).value.trim(),box=el('r'+s);
    if(q.length<3){box.style.display='none';return}
    fetch('/uji-partuturan/cari?kode='+encodeURIComponent(el('kode').value)+'&q='+encodeURIComponent(q))
     .then(function(r){return r.json()}).then(function(d){
       box.innerHTML='';box.style.display='block';
       if(d.galat){var x=document.createElement('div');x.className='kosong';x.textContent=d.galat;box.appendChild(x);return}
       if(!d.hasil.length){var y=document.createElement('div');y.className='kosong';y.textContent='Tidak ditemukan';box.appendChild(y);return}
       d.hasil.forEach(function(o){
         var b=document.createElement('button');b.type='button';b.textContent=o.label;
         b.addEventListener('click',function(){terpilih[s]=o;el('q'+s).value=o.nama;box.style.display='none';tampilDipilih(s);perbarui()});
         box.appendChild(b);
       });
     }).catch(function(){galat('Gagal mencari. Coba lagi.')});
  }
  ['a','b'].forEach(function(s){
    el('q'+s).addEventListener('input',function(){
      terpilih[s]=null;tampilDipilih(s);perbarui();
      clearTimeout(timer[s]);timer[s]=setTimeout(function(){cari(s)},300);
    });
  });
  el('tukar').addEventListener('click',function(){
    var t=terpilih.a;terpilih.a=terpilih.b;terpilih.b=t;
    var v=el('qa').value;el('qa').value=el('qb').value;el('qb').value=v;
    tampilDipilih('a');tampilDipilih('b');perbarui();
  });
  el('hitung').addEventListener('click',function(){
    galat('');el('hitung').disabled=true;
    fetch('/uji-partuturan/hitung?kode='+encodeURIComponent(el('kode').value)+'&a='+terpilih.a.id+'&b='+terpilih.b.id)
     .then(function(r){return r.json()}).then(function(d){
       perbarui();
       if(d.galat){galat(d.galat);return}
       el('la').textContent=terpilih.b.nama+' memanggil '+terpilih.a.nama;
       el('sa').textContent=d.sebutan_a;
       el('lb').textContent=terpilih.a.nama+' memanggil '+terpilih.b.nama;
       el('sb').textContent=d.sebutan_b;
       el('visual').innerHTML=d.visual;
       el('hasil').style.display='block';
       el('hasil').scrollIntoView({behavior:'smooth'});
     }).catch(function(){perbarui();galat('Gagal menghitung. Coba lagi.')});
  });
})();
</script>
</body>
</html>"""


class UjiPartuturanController(http.Controller):

    def _kode_valid(self, kode):
        """True bila kode benar. Bila parameter kode kosong, halaman nonaktif."""
        asli = request.env['ir.config_parameter'].sudo().get_param(PARAM_KODE) or ''
        if not asli:
            return False
        if not hmac.compare_digest(str(kode or '').encode(), asli.encode()):
            time.sleep(0.5)  # perlambat tebakan
            return False
        return True

    def _json(self, data, status=200):
        return Response(json.dumps(data), status=status, content_type='application/json; charset=utf-8',
                        headers=[('Cache-Control', 'no-store'), ('X-Robots-Tag', 'noindex')])

    def _aktif(self):
        return bool(request.env['ir.config_parameter'].sudo().get_param(PARAM_KODE))

    @http.route('/uji-partuturan', type='http', auth='public', website=False, csrf=False)
    def halaman(self, **kw):
        if not self._aktif():
            return Response('Halaman uji tidak aktif.', status=404, content_type='text/plain; charset=utf-8')
        return Response(_HALAMAN, content_type='text/html; charset=utf-8',
                        headers=[('Cache-Control', 'no-store'), ('X-Robots-Tag', 'noindex')])

    @http.route('/uji-partuturan/cari', type='http', auth='public', website=False, csrf=False)
    def cari(self, q='', kode='', **kw):
        if not self._aktif():
            return self._json({'galat': 'Halaman uji tidak aktif.'}, 404)
        if not self._kode_valid(kode):
            return self._json({'galat': 'Kode akses salah.'}, 403)
        q = (q or '').strip()
        if len(q) < MIN_HURUF:
            return self._json({'hasil': []})
        Orang = request.env['tarombo.orang'].sudo()
        rows = Orang.search([('name', 'ilike', q)], limit=MAKS_HASIL, order='name, sundut')
        hasil = [{
            'id': r.id,
            'nama': r.name,
            'label': r.with_context(tampil_ayah=True).display_name,
        } for r in rows]
        return self._json({'hasil': hasil})

    @http.route('/uji-partuturan/hitung', type='http', auth='public', website=False, csrf=False)
    def hitung(self, a='', b='', kode='', **kw):
        if not self._aktif():
            return self._json({'galat': 'Halaman uji tidak aktif.'}, 404)
        if not self._kode_valid(kode):
            return self._json({'galat': 'Kode akses salah.'}, 403)
        try:
            ia, ib = int(a), int(b)
        except (TypeError, ValueError):
            return self._json({'galat': 'Pilih Orang A dan Orang B terlebih dahulu.'}, 400)
        Orang = request.env['tarombo.orang'].sudo()
        oa, ob = Orang.browse(ia).exists(), Orang.browse(ib).exists()
        if not oa or not ob:
            return self._json({'galat': 'Orang tidak ditemukan.'}, 404)
        hasil = oa.hitung_partuturan(ob)
        return self._json({
            'sebutan_a': hasil['sebutan_a'] or '-',
            'sebutan_b': hasil['sebutan_b'] or '-',
            'jarak': hasil['jarak'],
            'visual': bangun_visual(oa, ob, hasil),
        })
