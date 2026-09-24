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
const WARNA_PUNGUAN = "#40916C";
const WARNA_MARGA = "#B5651D";
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
        });

        this.rootRef = useRef("root");
        this.donutRef = useRef("donut");
        this.sundutRef = useRef("sundut");
        this.punguanRef = useRef("punguan");
        this.margaRef = useRef("marga");
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
        this._renderBar(this.punguanRef, this.state.data.per_punguan, WARNA_PUNGUAN);
        this._renderBar(this.margaRef, this.state.data.per_marga, WARNA_MARGA);
        this._renderPeta();
    }

    _renderDonut() {
        const el = this.donutRef.el;
        if (!el) {
            return;
        }
        const chart = echarts.init(el);
        this._charts.push(chart);
        chart.setOption({
            tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
            color: [WARNA_JK.L, WARNA_JK.P],
            series: [
                {
                    type: "pie",
                    radius: ["45%", "70%"],
                    data: this.state.data.jenis_kelamin.map((d) => ({ name: d.name, value: d.value })),
                    label: { formatter: "{b}\n{c}", fontSize: 11 },
                    itemStyle: { borderRadius: 4, borderColor: "#fff", borderWidth: 2 },
                },
            ],
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
            tooltip: { trigger: "axis" },
            grid: { left: 36, right: 16, top: 16, bottom: 28 },
            xAxis: {
                type: "category",
                data: rows.map((r) => "Sundut " + r.sundut),
                boundaryGap: false,
                axisLabel: { fontSize: 10 },
            },
            yAxis: { type: "value", axisLabel: { fontSize: 10 } },
            series: [
                {
                    type: "line",
                    data: rows.map((r) => r.jumlah),
                    smooth: false,
                    symbol: "circle",
                    symbolSize: 6,
                    lineStyle: { color: WARNA_SUNDUT, width: 2.5 },
                    itemStyle: { color: WARNA_SUNDUT },
                    areaStyle: { color: "rgba(59, 111, 180, 0.12)" },
                },
            ],
        });
    }

    _renderBar(ref, rows, warna) {
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
            yAxis: { type: "value", axisLabel: { fontSize: 10 } },
            series: [
                {
                    type: "bar",
                    data: rows.map((r) => r.jumlah),
                    barMaxWidth: 28,
                    itemStyle: { color: warna, borderRadius: [4, 4, 0, 0] },
                },
            ],
        });
    }

    _renderPeta() {
        const el = this.mapRef.el;
        const points = this.state.data.map_points;
        if (!el || !window.L || !points.length) {
            return;
        }
        const map = L.map(el).setView([2.5, 99.0], 6);
        this._map = map;
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap",
        }).addTo(map);
        const icon = L.icon({
            iconUrl: "/tarombo/static/lib/leaflet/images/marker-icon.png",
            shadowUrl: "/tarombo/static/lib/leaflet/images/marker-shadow.png",
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
        });
        const markerList = points.map((p) => {
            const marker = L.marker([p.lat, p.lng], { icon }).addTo(map);
            marker.bindPopup(this._popupPeta(p), { minWidth: 220 });
            marker.on("popupopen", (ev) => {
                const tombol = ev.popup.getElement()?.querySelector(".o_tarombo_map_popup_btn");
                tombol?.addEventListener("click", () => this._bukaOrang(p.id));
            });
            return marker;
        });
        map.fitBounds(L.featureGroup(markerList).getBounds().pad(0.2));
        setTimeout(() => map.invalidateSize(), 150);
    }

    _escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    _popupPeta(p) {
        const fotoHtml = p.punya_foto
            ? `<img src="/web/image/tarombo.orang/${p.id}/foto" style="width:52px;height:52px;object-fit:cover;` +
              `border-radius:50%;float:left;margin-right:8px;" alt=""/>`
            : "";
        const genderLabel = p.jenis_kelamin === "P" ? "Perempuan" : "Laki-laki";
        const statusLabel = p.status === "sahih" ? "Terverifikasi" : "Belum Terverifikasi";
        return (
            `<div style="min-width:200px;">`
            + fotoHtml
            + `<div style="font-weight:600;">${this._escapeHtml(p.name)}</div>`
            + `<div style="font-size:11px;color:#666;">Sundut ${p.sundut} &middot; ${genderLabel}</div>`
            + `<div style="font-size:11px;color:#666;">${statusLabel} &middot; ${this._escapeHtml(p.punguan || "-")}</div>`
            + `<div style="clear:both;"></div>`
            + `<button type="button" class="o_tarombo_map_popup_btn btn btn-sm btn-primary w-100 mt-2">`
            + `Buka Data Lengkap</button>`
            + `</div>`
        );
    }

    _urlPratinjau(id) {
        return `/web/image/tarombo.arsip/${id}/pratinjau`;
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
