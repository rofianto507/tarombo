/** @odoo-module **/
// @ts-nocheck
// echarts dimuat sebagai aset modul biasa (static/lib/echarts/echarts.min.js),
// bukan lewat CDN, jadi tersedia sebagai variabel global `echarts` di sini —
// tidak di-`import` karena bukan modul ES.

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Layout } from "@web/search/layout";

const WARNA_STATUS = {
    sahih: "#3B6FB4",
    rumpang: "#ADB5BD",
};
const WARNA_TERTUTUP = "#E9ECEF";

export class PohonSilsilah extends Component {
    static template = "tarombo.PohonSilsilah";
    static components = { Layout };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.bodyRef = useRef("body");
        this.chartRef = useRef("chart");
        this.chart = null;
        this.display = { controlPanel: {}, searchPanel: false };

        const context = this.props.action.context || {};
        const orangId = context.active_id || this.props.action.params?.orang_id || false;

        this.state = useState({
            mode: "cabang",
            loading: true,
            error: false,
            orangId,
            pencarian: "",
            hasilPencarian: [],
        });
        this.currentData = null;
        this._pencarianTimer = null;
        // Cache foto bulat: id -> Promise<dataURL|false> dan id -> dataURL|false
        // (hasil sudah selesai). Simbol ECharts image:// tidak otomatis dipotong
        // bulat seperti CSS border-radius (itu render canvas, bukan DOM), jadi
        // foto di-crop jadi lingkaran sendiri lewat canvas sebelum dipakai.
        this._fotoPromise = new Map();
        this._fotoSiap = new Map();

        this._onResize = () => {
            this._aturTinggi();
            this.chart && this.chart.resize();
        };

        onMounted(() => {
            window.addEventListener("resize", this._onResize);
            this._aturTinggi();
            this._muatData();
        });

        onWillUnmount(() => {
            window.removeEventListener("resize", this._onResize);
            clearTimeout(this._pencarianTimer);
            if (this.chart) {
                this.chart.dispose();
                this.chart = null;
            }
        });
    }

    _aturTinggi() {
        // h-100/vh tidak menembus rantai layout Odoo (Layout > o_content) dengan
        // andal, jadi tinggi dihitung langsung dari sisa ruang viewport di bawah
        // header/breadcrumb, lalu di-set sebagai style eksplisit.
        if (!this.bodyRef.el) {
            return;
        }
        const top = this.bodyRef.el.getBoundingClientRect().top;
        const tinggi = Math.max(window.innerHeight - top - 16, 400);
        this.bodyRef.el.style.height = `${tinggi}px`;
    }

    async _gantiMode(mode) {
        if (this.state.mode === mode) {
            return;
        }
        this.state.mode = mode;
        await this._muatData();
    }

    _onInputPencarian(ev) {
        this.state.pencarian = ev.target.value;
        clearTimeout(this._pencarianTimer);
        const query = this.state.pencarian.trim();
        if (!query) {
            this.state.hasilPencarian = [];
            return;
        }
        this._pencarianTimer = setTimeout(() => this._cariNama(query), 300);
    }

    async _cariNama(query) {
        const hasil = await this.orm.searchRead(
            "tarombo.orang",
            [["name", "ilike", query]],
            ["id", "name", "sundut"],
            { limit: 8 }
        );
        // Buang hasil kalau kotak pencarian sudah berubah/dikosongkan saat request berjalan.
        if (this.state.pencarian.trim() === query) {
            this.state.hasilPencarian = hasil;
        }
    }

    _pilihHasilPencarian(id) {
        this.state.pencarian = "";
        this.state.hasilPencarian = [];
        this.state.orangId = id;
        this._muatData();
    }

    _resetTampilan() {
        if (!this.chart || !this.currentData) {
            return;
        }
        this.chart.dispose();
        this.chart = null;
        this._render(this.currentData);
    }

    _unduhGambar() {
        if (!this.chart) {
            return;
        }
        const url = this.chart.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
        const a = document.createElement("a");
        a.href = url;
        a.download = `pohon-silsilah-${this.state.orangId}.png`;
        a.click();
    }

    async _muatData() {
        if (!this.state.orangId) {
            this.state.loading = false;
            this.state.error = true;
            return;
        }
        this.state.loading = true;
        this.state.error = false;
        try {
            const data = await this.orm.call("tarombo.orang", "get_pohon_data", [
                this.state.orangId,
                this.state.mode,
            ]);
            if (!data || !data.id) {
                this.state.error = true;
            } else {
                await this._preloadFoto(data);
                this._render(data);
            }
        } catch {
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    _urlFoto(id) {
        return `/web/image/tarombo.orang/${id}/foto`;
    }

    _warnaStatus(node) {
        return node.collapsed ? WARNA_TERTUTUP : WARNA_STATUS[node.status] || WARNA_STATUS.rumpang;
    }

    _kumpulkanFoto(node, out = []) {
        if (node.punya_foto) {
            out.push({ id: node.id, warna: this._warnaStatus(node) });
        }
        (node.children || []).forEach((anak) => this._kumpulkanFoto(anak, out));
        return out;
    }

    async _preloadFoto(data) {
        const daftar = this._kumpulkanFoto(data).filter(
            (it) => !this._fotoPromise.has(`${it.id}_${it.warna}`)
        );
        await Promise.all(daftar.map((it) => this._fotoBulatPromise(it.id, it.warna)));
    }

    _fotoBulatPromise(id, warna) {
        const key = `${id}_${warna}`;
        if (!this._fotoPromise.has(key)) {
            const promise = this._potongFotoBulat(this._urlFoto(id), warna).then((hasil) => {
                this._fotoSiap.set(key, hasil);
                return hasil;
            });
            this._fotoPromise.set(key, promise);
        }
        return this._fotoPromise.get(key);
    }

    _potongFotoBulat(url, warnaBorder) {
        // Simbol image:// ECharts digambar di canvas dan tidak kena CSS
        // border-radius/border seperti DOM, jadi foto di-crop jadi lingkaran
        // dan diberi cincin border warna status (sesuai warna node aslinya)
        // langsung di canvas sebelum dipakai sebagai simbol node.
        const lebarBorder = 10;
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                try {
                    const ukuran = 96;
                    const radius = ukuran / 2;
                    const canvas = document.createElement("canvas");
                    canvas.width = ukuran;
                    canvas.height = ukuran;
                    const ctx = canvas.getContext("2d");
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(radius, radius, radius - lebarBorder, 0, Math.PI * 2);
                    ctx.closePath();
                    ctx.clip();
                    const sisi = Math.min(img.naturalWidth, img.naturalHeight);
                    const sx = (img.naturalWidth - sisi) / 2;
                    const sy = (img.naturalHeight - sisi) / 2;
                    ctx.drawImage(img, sx, sy, sisi, sisi, 0, 0, ukuran, ukuran);
                    ctx.restore();
                    ctx.beginPath();
                    ctx.arc(radius, radius, radius - lebarBorder / 2, 0, Math.PI * 2);
                    ctx.lineWidth = lebarBorder;
                    ctx.strokeStyle = warnaBorder;
                    ctx.stroke();
                    resolve(canvas.toDataURL("image/png"));
                } catch {
                    resolve(false);
                }
            };
            img.onerror = () => resolve(false);
            img.src = url;
        });
    }

    _ubahSimpul(node, jalurNama = []) {
        // jalur = nama leluhur dari akar pohon yang sedang ditampilkan sampai
        // simpul ini — dipakai buat tooltip breadcrumb, bukan silsilah absolut.
        const jalurBaru = [...jalurNama, node.name];
        const ukuran = node.selected ? 30 : 22;
        const warna = this._warnaStatus(node);
        const fotoBulat = node.punya_foto ? this._fotoSiap.get(`${node.id}_${warna}`) : false;
        return {
            id: String(node.id),
            name: node.name,
            value: { ...node, jalur: jalurBaru },
            symbol: fotoBulat
                ? `image://${fotoBulat}`
                : node.jenis_kelamin === "P" ? "diamond" : "circle",
            symbolSize: ukuran,
            itemStyle: {
                color: warna,
                borderColor: node.selected ? "#212529" : node.collapsed ? "#868e96" : "#ffffff",
                borderWidth: node.selected ? 4 : node.collapsed ? 2 : 1,
                borderType: node.collapsed ? "dashed" : "solid",
            },
            children: (node.children || []).map((anak) => this._ubahSimpul(anak, jalurBaru)),
        };
    }

    _escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    _tooltipHtml(params) {
        const node = params.data && params.data.value;
        if (!node) {
            return "";
        }
        const jalur = (node.jalur || [node.name]).map((n) => this._escapeHtml(n)).join(" &rsaquo; ");
        const genderLabel = node.jenis_kelamin === "P" ? "Perempuan" : "Laki-laki";
        const statusLabel = node.status === "sahih" ? "Terverifikasi" : "Belum Terverifikasi";
        const petunjuk = node.collapsed
            ? '<div style="font-size:11px;color:#868e96;margin-top:2px;">Klik untuk buka cabang</div>'
            : '<div style="font-size:11px;color:#868e96;margin-top:2px;">Klik untuk buka data &middot; klik kanan untuk fokus di sini</div>';
        const fotoHtml = node.punya_foto
            ? `<img src="${this._urlFoto(node.id)}" style="width:56px;height:56px;object-fit:cover;` +
              `border-radius:50%;float:left;margin-right:8px;" alt=""/>`
            : "";
        return (
            `<div style="max-width:280px;white-space:normal;overflow:hidden;">`
            + fotoHtml
            + `<div style="font-weight:600;">${jalur}</div>`
            + `<div style="font-size:11px;color:#666;">Sundut ${node.sundut} &middot; ${genderLabel} &middot; ${statusLabel}</div>`
            + petunjuk
            + `</div>`
        );
    }

    _render(data) {
        this.currentData = data;
        if (!this.chart) {
            this.chart = echarts.init(this.chartRef.el);
            this.chart.on("click", (params) => this._onKlikSimpul(params));
            this.chart.on("contextmenu", (params) => this._onKlikKananSimpul(params));
        }
        const radial = this.state.mode === "radial";
        const root = this._ubahSimpul(data);
        this.chart.setOption(
            {
                tooltip: { trigger: "item", formatter: (params) => this._tooltipHtml(params) },
                series: [
                    {
                        type: "tree",
                        data: [root],
                        layout: radial ? "radial" : "orthogonal",
                        orient: radial ? undefined : "TB",
                        roam: true,
                        expandAndCollapse: false,
                        initialTreeDepth: -1,
                        symbol: "circle",
                        label: {
                            fontSize: 11,
                            position: radial ? "right" : "top",
                            rotate: 0,
                        },
                        leaves: {
                            label: { position: radial ? "right" : "bottom" },
                        },
                        lineStyle: { color: "#adb5bd", width: 1.5 },
                        emphasis: { focus: "descendant" },
                        animationDuration: 300,
                    },
                ],
            },
            true
        );
        this.chart.resize();
    }

    _onKlikSimpul(params) {
        const node = params.data && params.data.value;
        if (!node) {
            return;
        }
        if (node.collapsed) {
            this.state.orangId = node.id;
            this._muatData();
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "tarombo.orang",
            res_id: node.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    _onKlikKananSimpul(params) {
        if (params.event && params.event.event) {
            params.event.event.preventDefault();
        }
        const node = params.data && params.data.value;
        if (!node || node.id === this.state.orangId) {
            return;
        }
        this.state.orangId = node.id;
        this._muatData();
    }
}

registry.category("actions").add("tarombo_pohon_silsilah", PohonSilsilah);