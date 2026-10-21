/** @odoo-module **/
// Butir "Manual Book" pada menu pengguna (pojok kanan atas), tepat setelah
// "My Preferences" (urutan 50). Halamannya dijaga di sisi server (khusus pengurus).

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

function manualItem() {
    return {
        type: "item",
        id: "tarombo_manual",
        description: _t("Manual Book"),
        callback: () => {
            browser.open("/tarombo/manual", "_blank");
        },
        sequence: 55,
    };
}

registry.category("user_menuitems").add("tarombo_manual", manualItem);
