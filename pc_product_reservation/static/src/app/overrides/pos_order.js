/** @odoo-module */
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        // Reservation reference: set when loading a reservation into the order
        // for payment. Used to mark the reservation as done after payment.
        this.pc_reservation_id = false;
        this.pc_reservation_name = false;
    },
});
