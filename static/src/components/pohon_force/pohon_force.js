/** @odoo-module **/
// @ts-nocheck
// Halaman penuh visualisasi pohon silsilah memakai ECharts graph (layout force).
// `echarts` tersedia sebagai variabel global (lihat manifest).

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Layout } from "@web/search/layout";
import { bangunOpsiGraf } from "./pohon_force_opsi";

const TUNDA_KLIK = 260; // ms, membedakan klik tunggal dan klik dua kali

export class TaromboPohonForce extends Component {
    static template = "tarombo.PohonForce";
    static components = { Layout };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.display = { controlPanel: {}, searchPanel: false };
        this.rootRef = useRef("root");
        this.canvasRef = useRef("canvas");

        this.state = useState({
            loading: true,
            error: false,
            kedalaman: 3,
            tampilLabel: true,
            jumlah: 0,
            terpotong: false,
            cari: "",
            hasil: [],
            akarId: false,
            bekerja: false,
        });

        this.chart = null;
        this.nodes = new Map(); // id -> simpul
        this.edges = new Map(); // "a>b" -> {source, target}
        this.anakDari = new Map(); // id -> Set(id anak yang sedang tampil)
        this._timerKlik = null;
        this._timerCari = null;

        this._onResize = () => {
            this._aturTinggi();
            this.chart && this.chart.resize();
        };

        onMounted(() => {
            window.addEventListener("resize", this._onResize);
            this._aturTinggi();
            this._buatChart();
            this._muatAwal();
        });
        onWillUnmount(() => {
            window.removeEventListener("resize", this._onResize);
            clearTimeout(this._timerKlik);
            clearTimeout(this._timerCari);
            this.chart && this.chart.dispose();
            this.chart = null;
        });
    }

    // ── tata letak ───────────────────────────────────────────────────────
    _aturTinggi() {
        if (!this.rootRef.el) {
            return;
        }
        const top = this.rootRef.el.getBoundingClientRect().top;
        this.rootRef.el.style.height = `${Math.max(window.innerHeight - top, 420)}px`;
    }

    _buatChart() {
        const el = this.canvasRef.el;
        if (!el || !window.echarts) {
            this.state.error = true;
            this.state.loading = false;
            return;
        }
        this.chart = echarts.init(el);
        this.chart.on("click", (p) => this._klikSimpul(p));
        this.chart.on("dblclick", (p) => this._klikGanda(p));
        // tooltip dibuat di sini karena butuh akses ke data simpul
        this._tooltip = (p) => {
            if (p.dataType === "edge") {
                return "";
            }
            const n = this.nodes.get(parseInt(p.data.id, 10));
            if (!n) {
                return "";
            }
            const jk = n.jk === "P" ? "Perempuan" : "Laki-laki";
            const sisa = Math.max(0, n.jumlah_anak - n.dimuat);
            return (
                `<div style="font-weight:700">${this._esc(n.name)}</div>` +
                `<div>Sundut ${n.sundut} · ${jk}</div>` +
                (n.ayah ? `<div>Ayah: ${this._esc(n.ayah)}</div>` : "") +
                `<div>${n.jumlah_anak} anak${sisa > 0 ? ` (${sisa} belum ditampilkan)` : ""}</div>` +
                `<div style="margin-top:4px;color:#888;font-size:11px">Klik: buka/tutup keturunan · Klik dua kali: buka profil</div>`
            );
        };
    }

    _esc(t) {
        const d = document.createElement("div");
        d.textContent = t || "";
        return d.innerHTML;
    }

    // ── data ────────────────────────────────────────────────────────────
    async _panggil(params) {
        return this.orm.call("tarombo.orang", "get_graf_pohon", [], params);
    }

    _kosongkan() {
        this.nodes.clear();
        this.edges.clear();
        this.anakDari.clear();
    }

    _gabung(data) {
        for (const n of data.nodes) {
            this.nodes.set(n.id, n);
        }
        for (const e of data.edges) {
            const kunci = `${e.source}>${e.target}`;
            if (!this.edges.has(kunci)) {
                this.edges.set(kunci, e);
                if (!this.anakDari.has(e.source)) {
                    this.anakDari.set(e.source, new Set());
                }
                this.anakDari.get(e.source).add(e.target);
            }
        }
        // jumlah anak yang sedang tampil dihitung ulang dari relasi yang ada
        for (const n of this.nodes.values()) {
            n.dimuat = (this.anakDari.get(n.id) || new Set()).size;
        }
        this.state.terpotong = this.state.terpotong || data.terpotong;
    }

    async _muatAwal() {
        await this._muat({ kedalaman: this.state.kedalaman });
    }

    async _muat(params) {
        this.state.bekerja = true;
        this.state.error = false;
        try {
            const data = await this._panggil(params);
            this._kosongkan();
            this.state.terpotong = false;
            this._gabung(data);
            this.state.akarId = data.akar_id;
            this._gambar(true);
        } catch {
            this.state.error = true;
        } finally {
            this.state.loading = false;
            this.state.bekerja = false;
        }
    }

    _simpanPosisi() {
        const peta = new Map();
        if (!this.chart) {
            return peta;
        }
        try {
            const seri = this.chart.getModel().getSeriesByIndex(0);
            const data = seri && seri.getData();
            if (data) {
                data.each((idx) => {
                    const l = data.getItemLayout(idx);
                    if (l) {
                        peta.set(parseInt(data.getId(idx), 10), [l[0], l[1]]);
                    }
                });
            }
        } catch {
            // belum ada tata letak sebelumnya
        }
        return peta;
    }

    _gambar(awal = false) {
        if (!this.chart) {
            return;
        }
        const posisi = awal ? new Map() : this._simpanPosisi();
        // simpul baru muncul di dekat ayahnya, bukan acak di pojok kanvas
        for (const n of this.nodes.values()) {
            if (!posisi.has(n.id) && n.ayah_id && posisi.has(n.ayah_id)) {
                const [x, y] = posisi.get(n.ayah_id);
                posisi.set(n.id, [x + (Math.random() - 0.5) * 40, y + 20 + Math.random() * 20]);
            }
        }
        const opsi = bangunOpsiGraf([...this.nodes.values()], [...this.edges.values()], {
            akarId: this.state.akarId,
            tampilLabel: this.state.tampilLabel,
            posisi,
        });
        opsi.tooltip.formatter = this._tooltip;
        this.chart.setOption(opsi, { notMerge: true });
        this.state.jumlah = this.nodes.size;
    }

    // ── interaksi ────────────────────────────────────────────────────────
    _klikSimpul(p) {
        if (p.dataType !== "node") {
            return;
        }
        clearTimeout(this._timerKlik);
        const id = parseInt(p.data.id, 10);
        this._timerKlik = setTimeout(() => this._toggle(id), TUNDA_KLIK);
    }

    _klikGanda(p) {
        if (p.dataType !== "node") {
            return;
        }
        clearTimeout(this._timerKlik);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "tarombo.orang",
            res_id: parseInt(p.data.id, 10),
            views: [[false, "form"]],
            target: "current",
        });
    }

    async _toggle(id) {
        const n = this.nodes.get(id);
        if (!n || this.state.bekerja) {
            return;
        }
        if (n.dimuat > 0) {
            this._ciutkan(id);
            this._gambar();
            return;
        }
        if (n.jumlah_anak > 0) {
            await this._perluas([id]);
        }
    }

    async _perluas(ids) {
        this.state.bekerja = true;
        try {
            const data = await this._panggil({ orang_ids: ids, kedalaman: 1 });
            this._gabung(data);
            this._gambar();
        } catch {
            this.state.error = true;
        } finally {
            this.state.bekerja = false;
        }
    }

    _ciutkan(id) {
        const anak = this.anakDari.get(id);
        if (!anak) {
            return;
        }
        for (const a of [...anak]) {
            this._ciutkan(a);
            this.nodes.delete(a);
            this.edges.delete(`${id}>${a}`);
        }
        this.anakDari.delete(id);
        const n = this.nodes.get(id);
        if (n) {
            n.dimuat = 0;
        }
    }

    // ── kontrol di bilah atas ────────────────────────────────────────────
    onUbahKedalaman(ev) {
        this.state.kedalaman = parseInt(ev.target.value, 10);
        this._muat({
            orang_id: this.state.akarId || false,
            kedalaman: this.state.kedalaman,
            dengan_leluhur: false,
        });
    }

    onAtasi() {
        // kembali ke leluhur acuan
        this.state.cari = "";
        this.state.hasil = [];
        this._muat({ kedalaman: this.state.kedalaman });
    }

    onToggleLabel() {
        this.state.tampilLabel = !this.state.tampilLabel;
        this._gambar();
    }

    onAturUlang() {
        this._gambar(true);
    }

    async onPerluasSatuTingkat() {
        const ids = [...this.nodes.values()]
            .filter((n) => n.dimuat === 0 && n.jumlah_anak > 0)
            .map((n) => n.id);
        if (ids.length) {
            await this._perluas(ids);
        }
    }

    onCiutkanSemua() {
        const akar = this.state.akarId;
        if (!akar) {
            return;
        }
        for (const a of [...(this.anakDari.get(akar) || [])]) {
            this._ciutkan(a);
            this.nodes.delete(a);
            this.edges.delete(`${akar}>${a}`);
        }
        this.anakDari.delete(akar);
        const n = this.nodes.get(akar);
        if (n) {
            n.dimuat = 0;
        }
        this._gambar();
    }

    onKetikCari(ev) {
        this.state.cari = ev.target.value;
        clearTimeout(this._timerCari);
        const q = this.state.cari.trim();
        if (q.length < 2) {
            this.state.hasil = [];
            return;
        }
        this._timerCari = setTimeout(async () => {
            const rows = await this.orm.searchRead(
                "tarombo.orang",
                [["name", "ilike", q]],
                ["name", "sundut", "ayah_id"],
                { limit: 10, order: "name, sundut" }
            );
            this.state.hasil = rows.map((r) => ({
                id: r.id,
                label: `${r.name} (sundut ${r.sundut})`,
                ayah: r.ayah_id ? r.ayah_id[1].replace(/ \(sundut .*\)$/, "") : "",
            }));
        }, 280);
    }

    pilihHasil(h) {
        this.state.cari = "";
        this.state.hasil = [];
        // tampilkan orang itu lengkap dengan leluhurnya dan 2 tingkat keturunan
        this._muat({ orang_id: h.id, kedalaman: 2, dengan_leluhur: true });
    }
}

registry.category("actions").add("tarombo_pohon_force", TaromboPohonForce);
