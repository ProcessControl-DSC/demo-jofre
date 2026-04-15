/** @odoo-module */
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    async onClickReserve() {
        await this.pos.createReservation();
    },
});
