/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

export class TransferRequestPopup extends Component {
    static template = "pc_pos_transfers.TransferRequestPopup";
    static components = { Dialog };
    static props = {
        productTemplate: { type: Object, optional: true },
        productId: { type: [Number, Boolean, { value: false }], optional: true },
        productName: { type: String, optional: true },
        warehouseName: { type: String, optional: true },
        availableQty: { type: Number, optional: true },
        availableWarehouses: { type: Array, optional: true },
        close: { type: Function },
    };

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");

        const warehouses = this.props.availableWarehouses || [];
        const firstWh = warehouses.length > 0 ? warehouses[0] : null;

        this.state = useState({
            qty: 1,
            selectedWarehouse: firstWh ? firstWh.name : '',
            selectedWarehouseQty: firstWh ? firstWh.qty : 0,
            isProcessing: false,
        });

        this.warehouses = warehouses;
    }

    get productName() {
        if (this.props.productName) return this.props.productName;
        if (this.props.productTemplate) {
            return this.props.productTemplate.display_name || this.props.productTemplate.name || '';
        }
        return 'Producto';
    }

    get maxQty() {
        return this.state.selectedWarehouseQty || this.props.availableQty || 99;
    }

    get hasWarehouses() {
        return this.warehouses.length > 0;
    }

    onWarehouseChange(ev) {
        const whName = ev.target.value;
        this.state.selectedWarehouse = whName;
        const wh = this.warehouses.find(w => w.name === whName);
        this.state.selectedWarehouseQty = wh ? wh.qty : 0;
        if (this.state.qty > this.state.selectedWarehouseQty) {
            this.state.qty = Math.max(1, this.state.selectedWarehouseQty);
        }
    }

    onQtyChange(ev) {
        let val = parseInt(ev.target.value, 10);
        if (isNaN(val) || val < 1) val = 1;
        if (val > this.maxQty) val = this.maxQty;
        this.state.qty = val;
    }

    incrementQty() {
        if (this.state.qty < this.maxQty) this.state.qty++;
    }

    decrementQty() {
        if (this.state.qty > 1) this.state.qty--;
    }

    async onConfirm() {
        if (!this.state.selectedWarehouse) {
            this.notification.add(_t("Seleccione un almacen de origen."), { type: "warning" });
            return;
        }
        this.state.isProcessing = true;
        try {
            const result = await this.pos.data.call(
                "stock.picking",
                "create_transfer_from_pos",
                [{
                    product_name: this.productName,
                    product_id: this.props.productId || false,
                    product_template_id: this.props.productTemplate?.id || false,
                    qty: this.state.qty,
                    source_warehouse_name: this.state.selectedWarehouse,
                    dest_warehouse_id: this.pos.getTransferWarehouseId(),
                }]
            );
            this.notification.add(
                _t("Traslado %s creado. Pendiente de preparacion.", result.name || ''),
                { type: "success" }
            );
            this.props.close();
        } catch (error) {
            this.notification.add(
                _t("Error al crear el traslado."),
                { type: "danger" }
            );
            this.state.isProcessing = false;
        }
    }

    onCancel() {
        this.props.close();
    }
}
