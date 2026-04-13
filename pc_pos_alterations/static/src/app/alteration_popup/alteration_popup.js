/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class AlterationPopup extends Component {
    static template = "pc_pos_alterations.AlterationPopup";
    static components = { Dialog };
    static props = {
        orderline: { type: Object, optional: true },
        order: { type: Object, optional: true },
        close: Function,
    };

    setup() {
        this.pos = usePos();
        const alterationTypes = this.pos.models["alteration.type"].getAll();
        const defaultType = alterationTypes.length > 0 ? alterationTypes[0] : null;
        const defaultDays = defaultType ? defaultType.default_duration_days : 3;
        const defaultCost = defaultType && defaultType.product_id
            ? defaultType.product_id.list_price
            : 0;

        const today = new Date();
        today.setDate(today.getDate() + defaultDays);
        const defaultDate = today.toISOString().split("T")[0];

        this.state = useState({
            alterationTypeId: defaultType ? defaultType.id : false,
            description: "",
            datePromised: defaultDate,
            deliveryMethod: "pickup_store",
            cost: defaultCost,
            tailorId: false,
        });

        this.alterationTypes = alterationTypes;
    }

    get productName() {
        if (this.props.orderline && this.props.orderline.product_id) {
            return this.props.orderline.product_id.display_name;
        }
        return "";
    }

    get partnerName() {
        const order = this.props.order || this.pos.getOrder();
        if (order && order.partner_id) {
            return order.partner_id.name;
        }
        return _t("Sin cliente");
    }

    onTypeChange(ev) {
        const typeId = parseInt(ev.target.value);
        this.state.alterationTypeId = typeId;
        const altType = this.alterationTypes.find((t) => t.id === typeId);
        if (altType) {
            const days = altType.default_duration_days || 3;
            const today = new Date();
            today.setDate(today.getDate() + days);
            this.state.datePromised = today.toISOString().split("T")[0];
            this.state.cost = altType.product_id ? altType.product_id.list_price : 0;
        }
    }

    onDescriptionChange(ev) {
        this.state.description = ev.target.value;
    }

    onDateChange(ev) {
        this.state.datePromised = ev.target.value;
    }

    onDeliveryMethodChange(ev) {
        this.state.deliveryMethod = ev.target.value;
    }

    async onClickConfirm() {
        if (!this.state.alterationTypeId) {
            return;
        }

        // 1. Buscar el tipo de arreglo y su producto asociado
        const altType = this.alterationTypes.find(
            (t) => t.id === this.state.alterationTypeId
        );
        if (!altType || !altType.product_id) {
            return;
        }

        // 2. Obtener el registro del producto desde los datos del POS
        const product = this.pos.models["product.product"].get(altType.product_id.id);
        if (!product) {
            console.error("Producto de arreglo no encontrado en el POS:", altType.product_id.id);
            return;
        }

        // 3. Añadir el producto de arreglo como nueva línea al pedido actual
        const order = this.props.order || this.pos.getOrder();
        const orderline = this.props.orderline;

        await this.pos.addLineToCurrentOrder(
            {
                product_tmpl_id: product.product_tmpl_id,
                price_unit: altType.product_id.list_price,
            },
            {},
            false
        );

        // 4. Configurar la línea recién añadida con nota y referencia a la prenda
        const newLine = order.getSelectedOrderline();
        if (newLine) {
            // Almacenar datos del arreglo en customer_note con formato parseable:
            // "descripción|fecha_prometida|método_entrega"
            const garmentName = orderline?.product_id?.display_name || "";
            const noteDesc = this.state.description
                ? `Arreglo para: ${garmentName}. ${this.state.description}`
                : `Arreglo para: ${garmentName}`;
            const noteData = `${noteDesc}|${this.state.datePromised}|${this.state.deliveryMethod}`;
            newLine.setCustomerNote(noteData);

            // Vincular la línea de arreglo a la línea de la prenda original
            if (orderline) {
                newLine.alteration_for_line_id = orderline;
            }
        }

        // 5. Cerrar el popup
        this.props.close();
    }

    onClickCancel() {
        this.props.close();
    }
}
