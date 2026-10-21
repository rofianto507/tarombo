/** @odoo-module **/
// @ts-nocheck
// echarts & Leaflet dimuat sebagai aset modul lokal (lihat manifest), tersedia
// sebagai variabel global `echarts`/`L`, sama seperti di pohon.js & geo_picker.js.

import { Component, useState, useRef, onMounted, onWillUnmount, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Layout } from "@web/search/layout";

const WARNA_JK = { L: "#3B6FB4", P: "#D6336C" };
const WARNA_PENDIDIKAN = "#40916C";
const WARNA_BIDANG = "#B5651D";
const WARNA_SUNDUT = "#3B6FB4";

export class TaromboDashboard extends Component {
    static template = "tarombo.Dashboard";
    static components = { Layout };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.display = { controlPanel: {}, searchPanel: false };

        this.state = useState({
            loading: true,
            error: false,
            data: null,
            levelPeta: "kabupaten",
        });

        this.rootRef = useRef("root");
        this.donutRef = useRef("donut");
        this.sundutRef = useRef("sundut");
        this.pendidikanRef = useRef("pendidikan");
        this.bidangRef = useRef("bidang");
        this.mapRef = useRef("map");
        this._charts = [];
        this._map = null;

        this._onResize = () => {
            this._aturTinggi();
            this._charts.forEach((c) => c.resize());
            if (this._map) {
                this._map.invalidateSize();
            }
        };

        useEffect(
            () => {
                if (this.state.data) {
                    this._aturTinggi();
                    this._renderSemua();
                }
            },
            () => [this.state.data]
        );

        onMounted(() => {
            window.addEventListener("resize", this._onResize);
            this._aturTinggi();
            this._muatData();
        });

        onWillUnmount(() => {
            window.removeEventListener("resize", this._onResize);
            this._bersihkan();
        });
    }

    _aturTinggi() {
        // h-100/vh tidak menembus rantai layout Odoo (Layout > o_content) dengan
        // andal, jadi tinggi dihitung langsung dari sisa ruang viewport di bawah
        // header/breadcrumb, sama seperti di pohon.js — supaya overflow-y:auto
        // di elemen ini benar-benar bisa scroll, bukan malah tinggi 0/auto.
        if (!this.rootRef.el) {
            return;
        }
        const top = this.rootRef.el.getBoundingClientRect().top;
        const tinggi = Math.max(window.innerHeight - top, 400);
        this.rootRef.el.style.height = `${tinggi}px`;
    }

    _bersihkan() {
        this._charts.forEach((c) => c.dispose());
        this._charts = [];
        if (this._map) {
            this._map.remove();
            this._map = null;
        }
    }

    async _muatData() {
        this.state.loading = true;
        this.state.error = false;
        this._bersihkan();
        try {
            this.state.data = await this.orm.call("tarombo.orang", "get_dashboard_data", []);
        } catch {
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    _renderSemua() {
        this._bersihkan();
        this._renderDonut();
        this._renderSundut();
        this._renderBar(this.pendidikanRef, this.state.data.per_pendidikan, WARNA_PENDIDIKAN, (r) =>
            this._bukaAnggota("pendidikan_tertinggi", r.key, "Anggota - Pendidikan " + r.name)
        );
        this._renderBar(this.bidangRef, this.state.data.per_bidang, WARNA_BIDANG, (r) =>
            this._bukaAnggota("bidang_kini_id", r.id, "Anggota - Bidang " + r.name)
        );
        this._renderPeta();
    }

    _renderDonut() {
        const el = this.donutRef.el;
        if (!el) {
            return;
        }
        const chart = echarts.init(el);
        this._charts.push(chart);
        const data = this.state.data.jenis_kelamin;
        const total = data.reduce((j, d) => j + d.value, 0);
        // Keterangan ditaruh di legenda (bawah), bukan label di irisan, supaya tidak
        // terpotong di kartu yang sempit. Total ditulis di tengah donat.
        chart.setOption({
            tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
            color: [WARNA_JK.L, WARNA_JK.P],
            title: {
                text: String(total),
                subtext: "anggota",
                left: "center",
                top: "31%",
                textStyle: { fontSize: 22, fontWeight: 700 },
                subtextStyle: { fontSize: 11 },
            },
            legend: {
                bottom: 4,
                itemWidth: 12,
                itemHeight: 12,
                textStyle: { fontSize: 11 },
                formatter: (nama) => {
                    const d = data.find((x) => x.name === nama);
                    if (!d) {
                        return nama;
                    }
                    const pct = total ? Math.round((d.value / total) * 1000) / 10 : 0;
                    return `${nama}: ${d.value} (${pct}%)`;
                },
            },
            series: [
                {
                    type: "pie",
                    radius: ["42%", "68%"],
                    center: ["50%", "42%"],
                    cursor: "pointer",
                    data: data.map((d) => ({ name: d.name, value: d.value, key: d.key })),
                    label: { show: false },
                    labelLine: { show: false },
                    itemStyle: { borderRadius: 4, borderColor: "#fff", borderWidth: 2 },
                },
            ],
        });
        chart.on("click", (p) => {
            if (p.data && p.data.key) {
                this._bukaAnggota("jenis_kelamin", p.data.key, "Anggota - " + p.name);
            }
        });
    }

    _renderSundut() {
        const el = this.sundutRef.el;
        const rows = this.state.data.per_sundut;
        if (!el || !rows.length) {
            return;
        }
        const chart = echarts.init(el);
        this._charts.push(chart);
        chart.setOption({
            tooltip: { trigger: "axis", formatter: (p) => `Sundut ${p[0].name}: ${p[0].value} anggota` },
            // containLabel + jarak kanan: label sumbu paling kanan tidak terpotong.
            grid: { left: 12, right: 28, top: 20, bottom: 34, containLabel: true },
            xAxis: {
                type: "category",
                data: rows.map((r) => String(r.sundut)),
                boundaryGap: false,
                axisLabel: { fontSize: 10, interval: 0 },
                name: "Sundut",
                nameLocation: "middle",
                nameGap: 22,
                nameTextStyle: { fontSize: 10 },
            },
            yAxis: { type: "value", minInterval: 1, axisLabel: { fontSize: 10 } },
            series: [
                {
                    type: "line",
                    data: rows.map((r) => r.jumlah),
                    smooth: false,
                    symbol: "circle",
                    symbolSize: 8,
                    cursor: "pointer",
                    lineStyle: { color: WARNA_SUNDUT, width: 2.5 },
                    itemStyle: { color: WARNA_SUNDUT },
                    areaStyle: { color: "rgba(59, 111, 180, 0.12)" },
                },
            ],
        });
        chart.on("click", (p) => {
            const baris = rows[p.dataIndex];
            if (baris) {
                this._bukaAnggota("sundut", baris.sundut, "Anggota - Sundut " + baris.sundut);
            }
        });
    }

    _renderBar(ref, rows, warna, onClick) {
        const el = ref.el;
        if (!el || !rows.length) {
            return;
        }
        const chart = echarts.init(el);
        this._charts.push(chart);
        chart.setOption({
            tooltip: { trigger: "axis" },
            grid: { left: 10, right: 16, top: 16, bottom: 60, containLabel: true },
            xAxis: {
                type: "category",
                data: rows.map((r) => r.name),
                axisLabel: { rotate: 35, fontSize: 10, interval: 0 },
            },
            yAxis: { type: "value", minInterval: 1, axisLabel: { fontSize: 10 } },
            series: [
                {
                    cursor: "pointer",
                    type: "bar",
                    data: rows.map((r) => r.jumlah),
                    barMaxWidth: 28,
                    itemStyle: { color: warna, borderRadius: [4, 4, 0, 0] },
                },
            ],
        });
        chart.on("click", (p) => {
            const baris = rows[p.dataIndex];
            if (baris && onClick) {
                onClick(baris);
            }
        });
    }

    // Sebaran anggota per wilayah: marker berisi jumlah anggota, pilihan
    // tingkat Provinsi / Kabupaten-Kota. Tidak ada titik atau nama individu.
    _renderPeta() {
        const el = this.mapRef.el;
        const sebaran = this.state.data.sebaran_wilayah;
        if (!el || !window.L || !sebaran) {
            return;
        }
        const map = L.map(el).setView([2.5, 99.0], 6);
        this._map = map;
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap",
        }).addTo(map);
        // Grouping marker (Leaflet.markercluster): titik wilayah yang berdekatan
        // digabung menjadi satu gelembung berisi total anggotanya, dan terurai saat
        // peta diperbesar. Angka gelembung = jumlah anggota, bukan jumlah titik.
        this._lapisMarker = L.markerClusterGroup({
            maxClusterRadius: 55,
            showCoverageOnHover: false,
            spiderfyOnMaxZoom: true,
            zoomToBoundsOnClick: true,
            iconCreateFunction: (cluster) => {
                const total = cluster
                    .getAllChildMarkers()
                    .reduce((jml, m) => jml + (m.options.jumlahAnggota || 0), 0);
                const d = Math.round(40 + Math.min(30, Math.log10(total + 1) * 12));
                return L.divIcon({
                    html: `<div class="o_tarombo_cluster_marker" style="width:${d}px;height:${d}px;line-height:${d - 6}px;">${total}</div>`,
                    className: "",
                    iconSize: [d, d],
                    iconAnchor: [d / 2, d / 2],
                });
            },
        }).addTo(map);
        this._gambarMarker(true);
        setTimeout(() => map.invalidateSize(), 150);
    }

    _gambarMarker(sesuaikan) {
        if (!this._map || !this._lapisMarker) {
            return;
        }
        this._lapisMarker.clearLayers();
        const level = this.state.levelPeta;
        // Kolom yang dipakai penghitung sebaran (get_sebaran_wilayah), supaya daftar
        // anggota yang dibuka persis sama dengan jumlah yang tertera di peta.
        const kolom = level === "provinsi" ? "provinsi_id" : "kabupaten_id";
        const items = this.state.data.sebaran_wilayah[level] || [];
        const markers = items.map((w) => {
            const d = Math.round(30 + Math.min(28, Math.log10(w.jumlah + 1) * 14));
            const icon = L.divIcon({
                className: "",
                html: `<div class="o_tarombo_sebaran_marker" style="width:${d}px;height:${d}px;line-height:${d}px;">${w.jumlah}</div>`,
                iconSize: [d, d],
            });
            const marker = L.marker([w.lat, w.lng], { icon, jumlahAnggota: w.jumlah });
            marker.bindPopup(
                `<div style="font-weight:600;">${this._escapeHtml(w.nama)}</div>`
                + `<div style="font-size:11px;color:#666;">${this._escapeHtml(w.nama_lengkap)}</div>`
                + `<button type="button" class="btn btn-sm btn-primary o_tarombo_popup_lihat" style="margin-top:8px;">`
                + `Lihat ${w.jumlah} anggota</button>`
            );
            marker.on("popupopen", (e) => {
                const tombol = e.popup.getElement().querySelector(".o_tarombo_popup_lihat");
                if (tombol) {
                    tombol.onclick = () =>
                        this._bukaDaftar(
                            "tarombo.action_tarombo_orang",
                            [[kolom, "=", w.id]],
                            "Anggota - " + w.nama
                        );
                }
            });
            marker.addTo(this._lapisMarker);
            return marker;
        });
        if (sesuaikan && markers.length) {
            this._map.fitBounds(L.featureGroup(markers).getBounds().pad(0.2));
        }
    }

    setLevelPeta(level) {
        this.state.levelPeta = level;
        this._gambarMarker(true);
    }

    _escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    _urlPratinjau(id) {
        return `/web/image/tarombo.arsip/${id}/pratinjau`;
    }

    /**
     * Buka daftar data dari sebuah KPI. Memakai action yang sudah ada (tampilan
     * list/form/dll. tetap sama), hanya domain-nya yang dipersempit.
     */
    async _bukaDaftar(xmlid, domain = [], nama = false) {
        const action = await this.actionService.loadAction(xmlid);
        action.domain = domain;
        action.context = {};
        action.target = "current";
        if (nama) {
            action.name = nama;
        }
        this.actionService.doAction(action);
    }

    /** Nilai terbesar kolom Total di tabel domisili, untuk lebar batang kecil per baris. */
    get maksDomisili() {
        const baris = (this.state.data && this.state.data.tabel_domisili) || [];
        return Math.max(1, ...baris.map((r) => r.total));
    }

    /** Warna lencana jenis usulan. */
    _kelasJenis(jenis) {
        const j = (jenis || "").toLowerCase();
        if (j.includes("tambah")) {
            return "o_tarombo_pil--hijau";
        }
        if (j.includes("koreksi")) {
            return "o_tarombo_pil--emas";
        }
        if (j.includes("istri")) {
            return "o_tarombo_pil--ungu";
        }
        return "o_tarombo_pil--biru";
    }

    /** Buka anggota di wilayah pada baris tabel domisili (kabupaten, provinsi saja, atau tanpa domisili). */
    _bukaDomisili(row) {
        const id = String(row.id);
        let domain;
        if (id.startsWith("k")) {
            domain = [["kabupaten_id", "=", parseInt(id.slice(1), 10)]];
        } else if (id.startsWith("p")) {
            domain = [
                ["provinsi_id", "=", parseInt(id.slice(1), 10)],
                ["kabupaten_id", "=", false],
            ];
        } else {
            domain = [
                ["provinsi_id", "=", false],
                ["kabupaten_id", "=", false],
            ];
        }
        const nama = String(row.name).split(" - ").slice(-1)[0];
        return this._bukaDaftar("tarombo.action_tarombo_orang", domain, "Anggota - " + nama);
    }

    _bukaPohonForce() {
        this.actionService.doAction("tarombo.action_tarombo_pohon_force");
    }

    _bukaAnggota(kolom, nilai, judul) {
        return this._bukaDaftar("tarombo.action_tarombo_orang", [[kolom, "=", nilai]], judul);
    }

    _bukaOrang(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "tarombo.orang",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    _bukaUsulan(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "tarombo.usulan",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    _bukaArsip(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "tarombo.arsip",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("tarombo_dashboard", TaromboDashboard);
