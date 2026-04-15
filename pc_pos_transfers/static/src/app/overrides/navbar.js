/** @odoo-module */
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this._transferDialog = useService("dialog");
    },
    async onClickTransfers() {
        // Lazy import to avoid breaking navbar if TransferScreen has issues
        const { TransferScreen } = await odoo.loader.modules.get(
            "@pc_pos_transfers/app/transfer_screen/transfer_screen"
        ) || {};
        if (TransferScreen) {
            this._transferDialog.add(TransferScreen, {});
        }
    },
});
