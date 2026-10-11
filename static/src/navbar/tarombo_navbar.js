/** @odoo-module **/
// Odoo bawaan tidak menandai butir menu atas yang sedang dibuka (hanya :hover,
// :focus, dan dropdown yang sedang terbuka). Patch ini menambahkan kelas
// `o_tarombo_menu_aktif` pada butir menu atas yang memuat aksi yang sedang
// tampil, supaya bisa diberi garis emas di tarombo_navbar.scss.

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { onMounted, onPatched, onWillUnmount } from "@odoo/owl";

const KELAS_AKTIF = "o_tarombo_menu_aktif";

function memuatAksi(menu, actionId) {
    if (menu.actionID === actionId) {
        return true;
    }
    return (menu.childrenTree || []).some((anak) => memuatAksi(anak, actionId));
}

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this._taromboMenuAktif = null;
        const tandai = () => this._taromboTandaiMenuAktif();
        this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", tandai);
        onWillUnmount(() => this.env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", tandai));
        onMounted(tandai);
        onPatched(tandai);
    },

    _taromboTandaiMenuAktif() {
        const el = this.appSubMenus.el;
        if (!el) {
            return;
        }
        const actionId = this.actionService.currentController?.action?.id;
        const seksi =
            actionId && (this.currentAppSections || []).find((s) => memuatAksi(s, actionId));
        // Aksi yang tidak ada di menu (mis. Pohon Silsilah dibuka dari form
        // Anggota) tidak mengubah penanda: menu asalnya tetap dianggap aktif.
        if (seksi) {
            this._taromboMenuAktif = seksi.xmlid;
        }
        for (const butir of el.querySelectorAll("[data-menu-xmlid]")) {
            butir.classList.toggle(
                KELAS_AKTIF,
                Boolean(this._taromboMenuAktif) && butir.dataset.menuXmlid === this._taromboMenuAktif
            );
        }
    },
});
