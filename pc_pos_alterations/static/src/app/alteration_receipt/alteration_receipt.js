/** @odoo-module */
import { Component } from "@odoo/owl";

export class AlterationReceipt extends Component {
    static template = "pc_pos_alterations.AlterationReceipt";
    static props = {
        alteration: Object,
    };

    get storeName() {
        return this.props.alteration.store_name || this.props.alteration.warehouse_name || "";
    }

    get storeAddress() {
        return this.props.alteration.store_address || "";
    }

    get currentDateTime() {
        return this.props.alteration.date || new Date().toLocaleString("es-ES");
    }

    get customerName() {
        return this.props.alteration.partner_name || "Sin identificar";
    }

    get customerPhone() {
        return this.props.alteration.partner_phone || "";
    }

    get productName() {
        return this.props.alteration.product_name || "N/A";
    }

    get productRef() {
        return this.props.alteration.product_ref || "";
    }

    get alterationType() {
        return this.props.alteration.alteration_type || "";
    }

    get description() {
        return this.props.alteration.description || "";
    }

    get deliveryMethodText() {
        const method = this.props.alteration.delivery_method;
        if (method === "pickup_store") {
            return "Recogida en tienda";
        }
        if (method === "ship_customer") {
            return "Envio a domicilio";
        }
        return "";
    }

    get formattedDatePromised() {
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

    get orderReference() {
        return this.props.alteration.order_ref || this.props.alteration.name || "";
    }

    get stateLabel() {
        const labels = {
            draft: "Borrador",
            confirmed: "Confirmada",
            under_repair: "En Curso",
            done: "Finalizada",
            cancel: "Cancelada",
        };
        return labels[this.props.alteration.state] || this.props.alteration.state || "";
    }
}
