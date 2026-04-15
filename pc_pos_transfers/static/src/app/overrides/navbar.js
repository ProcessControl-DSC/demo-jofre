/** @odoo-module */
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { TransferScreen } from "@pc_pos_transfers/app/transfer_screen/transfer_screen";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
    },
    onClickTransfers() {
        this.dialog.add(TransferScreen, {});
    },
});
