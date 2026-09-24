/** @odoo-module **/
// @ts-nocheck
// Leaflet dimuat sebagai aset modul lokal (static/lib/leaflet/), bukan CDN —
// tersedia sebagai variabel global `L` di sini, tidak di-`import` (bukan modul ES).

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onWillUnmount, useRef, useEffect } from "@odoo/owl";

// Titik awal peta kosong: sekitar Sumatera Utara.
const DEFAULT_LAT = 2.5;
const DEFAULT_LNG = 99.0;
const DEFAULT_ZOOM = 7;
const MARKED_ZOOM = 14;

export class TaromboGeoPicker extends Component {
    static template = "tarombo.GeoPicker";
    static props = {
        ...standardFieldProps,
        latField: { type: String, optional: true },
        lngField: { type: String, optional: true },
    };

    setup() {
        this.mapContainer = useRef("mapDiv");
        this.map = null;
        this.marker = null;

        // Nama field lat/lng bisa dikunci eksplisit lewat options (mis. model
        // dengan field bukan bernama persis latitude/longitude, seperti
        // usul_latitude/usul_longitude di tarombo.usulan). Kalau tidak
        // dikunci, dideteksi otomatis seperti sebelumnya.
        const fields = this.props.record.fields || {};
        this.latField = this.props.latField || ('latitude' in fields ? 'latitude' : 'lat');
        this.lngField = this.props.lngField || ('longitude' in fields ? 'longitude' : 'lng');

        useEffect(
            () => this._renderOrUpdate(),
            () => [
                this.props.record.data[this.latField],
                this.props.record.data[this.lngField],
                this.props.readonly,
            ]
        );

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
                this.map = null;
            }
        });
    }

    _icon() {
        return L.icon({
            iconUrl: '/tarombo/static/lib/leaflet/images/marker-icon-red.png',
            shadowUrl: '/tarombo/static/lib/leaflet/images/marker-shadow.png',
            iconSize: [25, 41],
            iconAnchor: [12, 41],
            popupAnchor: [1, -34],
            shadowSize: [41, 41],
            shadowAnchor: [12, 41],
        });
    }

    _renderOrUpdate() {
        if (!this.mapContainer.el || !window.L) {
            return;
        }
        const data = this.props.record.data;
        const ada = Boolean(data[this.latField] && data[this.lngField]);
        const lat = ada ? data[this.latField] : DEFAULT_LAT;
        const lng = ada ? data[this.lngField] : DEFAULT_LNG;

        if (!this.map) {
            this.map = L.map(this.mapContainer.el).setView([lat, lng], ada ? MARKED_ZOOM : DEFAULT_ZOOM);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; OpenStreetMap',
            }).addTo(this.map);

            this.marker = L.marker([lat, lng], {
                icon: this._icon(),
                draggable: !this.props.readonly,
                opacity: ada ? 1 : 0,
            }).addTo(this.map);

            if (!this.props.readonly) {
                this.marker.on('dragend', () => this._tulisKoordinat(this.marker.getLatLng()));
                this.map.on('click', (ev) => {
                    this.marker.setLatLng(ev.latlng);
                    this.marker.setOpacity(1);
                    this._tulisKoordinat(ev.latlng);
                });
            }

            setTimeout(() => this.map && this.map.invalidateSize(), 150);
        } else {
            this.marker.setLatLng([lat, lng]);
            this.marker.setOpacity(ada ? 1 : 0);
            this.marker.dragging[this.props.readonly ? 'disable' : 'enable']();
        }
    }

    _tulisKoordinat(pos) {
        this.props.record.update({
            [this.latField]: pos.lat,
            [this.lngField]: pos.lng,
        });
    }

    get koordinatText() {
        const data = this.props.record.data;
        const lat = data[this.latField];
        const lng = data[this.lngField];
        if (lat && lng) {
            return `Latitude ${lat.toFixed(6)}, Longitude ${lng.toFixed(6)}`;
        }
        return 'Belum ada titik lokasi';
    }
}

registry.category("fields").add("tarombo_geo_picker", {
    component: TaromboGeoPicker,
    displayName: "Peta Titik Lokasi",
    supportedTypes: ["float"],
    extractProps: ({ options }) => ({
        latField: options?.lat_field,
        lngField: options?.lng_field,
    }),
});
