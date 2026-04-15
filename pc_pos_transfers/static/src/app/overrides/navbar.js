/** @odoo-module */
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    onClickTransfers() {
        const mod = odoo.loader.modules.get("@pc_pos_transfers/app/transfer_screen/transfer_screen");
        if (mod && mod.TransferScreen) {
            this.dialog.add(mod.TransferScreen, {});
        } else {
            alert("Módulo de traslados no disponible");
        }
    },
});
