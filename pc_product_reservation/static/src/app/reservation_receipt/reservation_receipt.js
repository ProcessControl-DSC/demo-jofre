/** @odoo-module */
import { Component } from "@odoo/owl";

/**
 * ReservationReceipt - Receipt component for a reservation confirmation.
 * This component is used to render a printable receipt when a reservation
 * is created from the POS.
 */
export class ReservationReceipt extends Component {
    static template = "pc_product_reservation.ReservationReceipt";
    static props = {
        reservation: { type: Object },
    };

    get totalAmount() {
        const lines = this.props.reservation.lines || [];
        return lines.reduce((acc, l) => acc + l.product_qty * l.price_unit, 0);
    }
}
