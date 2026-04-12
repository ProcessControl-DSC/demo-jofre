/** @odoo-module */
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ReservationListPopup } from "@pc_product_reservation/app/reservation_screen/reservation_screen";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },
    async onClickReservations() {
        this.dialog.add(ReservationListPopup, {});
    },
});
