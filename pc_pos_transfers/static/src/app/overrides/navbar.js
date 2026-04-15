/** @odoo-module */
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { TransferScreen } from "@pc_pos_transfers/app/transfer_screen/transfer_screen";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },
    async onClickTransfers() {
        this.dialog.add(TransferScreen, {});
    },
});
