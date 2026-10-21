/** @odoo-module **/
// @ts-nocheck
// Pembuat opsi ECharts untuk grafik pohon (layout force). Sengaja berupa fungsi
// murni tanpa import, supaya mudah diuji terpisah dari komponen OWL.

export const WARNA_L = "#3B6FB4";
export const WARNA_P = "#D6336C";
export const WARNA_AKAR = "#C8A24A";

/**
 * @param {Array} nodes  simpul: {id, name, sundut, jk, status, ayah, jumlah_anak, dimuat}
 * @param {Array} edges  garis: {source, target}
 * @param {Object} opts  {akarId, tampilLabel, posisi: Map(id -> [x, y])}
 */
export function bangunOpsiGraf(nodes, edges, opts = {}) {
    const { akarId = null, tampilLabel = true, posisi = new Map() } = opts;
    const data = nodes.map((n) => {
        const sisa = Math.max(0, (n.jumlah_anak || 0) - (n.dimuat || 0));
        const akar = n.id === akarId;
        const ukuran = 11 + Math.min(28, Math.sqrt(n.jumlah_anak || 0) * 5) + (akar ? 6 : 0);
        const item = {
            id: String(n.id),
            name: n.name,
            value: n.sundut,
            category: n.jk === "P" ? 1 : 0,
            symbolSize: ukuran,
            // Simpul yang keturunannya belum dimuat diberi cincin emas dan tanda (+N).
            itemStyle: sisa > 0 || akar
                ? { borderColor: WARNA_AKAR, borderWidth: akar ? 4 : 3 }
                : { borderColor: "#fff", borderWidth: 1.5 },
            label: {
                show: tampilLabel,
                formatter: sisa > 0 ? `${n.name} (+${sisa})` : n.name,
            },
        };
        const p = posisi.get(n.id);
        if (p) {
            item.x = p[0];
            item.y = p[1];
        }
        return item;
    });
    const links = edges.map((e) => ({ source: String(e.source), target: String(e.target) }));
    return {
        animationDuration: 900,
        animationEasingUpdate: "quinticInOut",
        legend: [{ data: ["Laki-laki", "Perempuan"], top: 8, right: 12, textStyle: { fontSize: 12 } }],
        color: [WARNA_L, WARNA_P],
        tooltip: { confine: true },
        series: [
            {
                type: "graph",
                layout: "force",
                data,
                links,
                categories: [{ name: "Laki-laki" }, { name: "Perempuan" }],
                roam: true,
                draggable: true,
                zoom: 1,
                scaleLimit: { min: 0.2, max: 8 },
                label: { position: "right", fontSize: 11, color: "#1d2a22" },
                labelLayout: { hideOverlap: true },
                edgeSymbol: ["none", "arrow"],
                edgeSymbolSize: [0, 7],
                lineStyle: { color: "#9aa8a0", width: 1.4, opacity: 0.7, curveness: 0.08 },
                emphasis: {
                    focus: "adjacency",
                    lineStyle: { width: 4, opacity: 1 },
                    label: { show: true, fontWeight: 700 },
                },
                force: {
                    repulsion: 230,
                    gravity: 0.06,
                    edgeLength: [34, 95],
                    friction: 0.12,
                    layoutAnimation: true,
                },
                cursor: "pointer",
            },
        ],
    };
}
