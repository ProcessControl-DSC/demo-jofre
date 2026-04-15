/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * TransferRequestPopup - Popup to specify quantity and confirm a transfer request.
 *
 * Shows the product, source warehouse, available qty and a quantity input.
 * On confirm, creates an internal transfer via RPC.
 */
export class TransferRequestPopup extends Component {
    static template = "pc_pos_transfers.TransferRequestPopup";
    static components = { Dialog };
    static props = {
        productTemplate: { type: Object, optional: true },
        productId: { type: [Number, Boolean, { value: false }], optional: true },
        warehouseName: { type: String, optional: true },
        availableQty: { type: Number, optional: true },
        availableWarehouses: { type: Array, optional: true },
        close: { type: Function },
    };

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");
        this.state = useState({
            qty: 1,
            isProcessing: false,
        });
    }

    get maxQty() {
        return this.props.availableQty || 0;
    }

    get productName() {
        const tmpl = this.props.productTemplate;
        return tmpl.display_name || tmpl.displayName || tmpl.name || "";
    }

    onQtyChange(ev) {
        let val = parseInt(ev.target.value, 10);
        if (isNaN(val) || val < 1) {
            val = 1;
        }
        if (val > this.maxQty) {
            val = this.maxQty;
        }
        this.state.qty = val;
    }

    incrementQty() {
        if (this.state.qty < this.maxQty) {
            this.state.qty++;
        }
    }

    decrementQty() {
        if (this.state.qty > 1) {
            this.state.qty--;
        }
    }

    async onConfirm() {
        if (this.state.isProcessing) {
            return;
        }
        this.state.isProcessing = true;

        try {
            // Resolve the product_id (product.product) to use
            let productId = this.props.productId;

            // If we don't have a direct product.product id, try to find it
            if (!productId) {
                const tmpl = this.props.productTemplate;
                // Search for the first variant
                if (tmpl.product_variant_ids) {
                    const variants = tmpl.product_variant_ids;
                    if (Array.isArray(variants) && variants.length > 0) {
                        productId = typeof variants[0] === "object" ? variants[0].id : variants[0];
                    }
                }
                // Fallback: search in local POS models cache
                if (!productId && tmpl.id) {
                    const products = this.pos.models["product.product"].filter(
                        (p) => p.product_tmpl_id && (p.product_tmpl_id.id || p.product_tmpl_id) === tmpl.id
                    );
                    if (products.length > 0) {
                        productId = products[0].id;
                    }
                }
            }

            // If still no productId, we'll send the template ID and let the backend resolve
            const templateId = this.props.productTemplate?.id || false;

            if (!productId && !templateId) {
                this.notification.add(
                    _t("No se ha podido identificar el producto."),
                    { type: "danger" }
                );
                this.state.isProcessing = false;
                return;
            }

            const destWhId = this.pos.getTransferWarehouseId();
            if (!destWhId) {
                this.notification.add(
                    _t("No se ha podido determinar el almacén del TPV."),
                    { type: "danger" }
                );
                this.state.isProcessing = false;
                return;
            }

            // Get the employee/cashier name
            const cashier = this.pos.getCashier();
            const userName = cashier ? (cashier.name || cashier.display_name || "") : "";

            // Send warehouse name — backend resolves it to ID
            const params = {
                qty: this.state.qty,
                source_warehouse_name: this.props.warehouseName,
                dest_warehouse_id: destWhId,
                user_name: userName,
            };
            if (productId) {
                params.product_id = productId;
            } else {
                params.product_template_id = templateId;
            }
            const result = await this.pos.createTransferFromPos(params);

            if (result) {
                this.props.close();
            }
        } catch (error) {
            console.error("Error creating transfer:", error);
        } finally {
            this.state.isProcessing = false;
        }
    }

    onCancel() {
        this.props.close();
    }
}
