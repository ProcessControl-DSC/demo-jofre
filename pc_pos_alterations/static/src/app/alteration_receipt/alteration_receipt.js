/** @odoo-module */
import { Component } from "@odoo/owl";

export class AlterationReceipt extends Component {
    static template = "pc_pos_alterations.AlterationReceipt";
    static props = {
        alteration: Object,
    };

    get deliveryMethodText() {
        const method = this.props.alteration.delivery_method;
        if (method === "pickup_store") {
            return "Recogida en tienda";
        }
        if (method === "ship_customer") {
            return "Envío a domicilio";
        }
        return "";
    }

    get formattedDate() {
        const dateStr = this.props.alteration.date_promised;
        if (!dateStr) {
            return "";
        }
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString("es-ES", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric",
            });
        } catch {
            return dateStr;
        }
    }

    get formattedCost() {
        const cost = this.props.alteration.cost || 0;
        return cost.toFixed(2);
    }
}
