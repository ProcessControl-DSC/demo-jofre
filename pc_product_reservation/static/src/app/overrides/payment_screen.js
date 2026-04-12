/** @odoo-module */
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    async afterOrderValidation(suggestToSync = false) {
        await super.afterOrderValidation(...arguments);

        // After a successful payment, if the order was loaded from a reservation,
        // mark the reservation as done (paid) in the backend.
        if (this.order.pc_reservation_id) {
            await this.pos.markReservationDoneIfNeeded(this.order);
        }
    },
});
