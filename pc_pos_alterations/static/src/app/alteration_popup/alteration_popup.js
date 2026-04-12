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
        getPayload: { type: Function, optional: true },
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

        const order = this.props.order || this.pos.getOrder();
        const orderline = this.props.orderline;

        const vals = {
            alteration_type_id: this.state.alterationTypeId,
            description: this.state.description,
            date_promised: this.state.datePromised,
            delivery_method: this.state.deliveryMethod,
            cost: this.state.cost,
            tailor_id: this.state.tailorId || false,
            pos_order_id: order.id || false,
            pos_order_line_id: orderline ? orderline.id || false : false,
            partner_id: order.partner_id ? order.partner_id.id : false,
            product_id: orderline ? orderline.product_id.id : false,
        };

        try {
            const result = await this.pos.createAlteration(vals);
            if (this.props.getPayload) {
                this.props.getPayload(result);
            }
            this.props.close();
        } catch (error) {
            console.error("Error creating alteration:", error);
        }
    }

    onClickCancel() {
        this.props.close();
    }
}
