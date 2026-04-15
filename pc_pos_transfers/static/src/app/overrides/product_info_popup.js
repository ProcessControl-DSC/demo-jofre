/** @odoo-module */
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { TransferRequestPopup } from "@pc_pos_transfers/app/transfer_request/transfer_request_popup";

patch(ProductInfoPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    /**
     * Get the current POS warehouse ID.
     */
    getCurrentWarehouseId() {
        return this.pos.getTransferWarehouseId();
    },

    /**
     * Check if a warehouse is the current store (should not show request button).
     * We compare warehouse names since the popup data contains warehouse names.
     */
    isCurrentWarehouse(warehouseName) {
        const currentWhId = this.getCurrentWarehouseId();
        if (!currentWhId) {
            return false;
        }
        // Try to match by warehouse_id from config
        const configWh = this.pos.config.warehouse_id;
        if (configWh) {
            const configWhName = configWh.name || configWh.display_name || "";
            if (configWhName === warehouseName) {
                return true;
            }
        }
        return false;
    },

    /**
     * Check if a warehouse has available stock to request.
     */
    canRequestFromWarehouse(warehouse) {
        return warehouse.free_qty > 0 && !this.isCurrentWarehouse(warehouse.name);
    },

    /**
     * Open the transfer request popup for a specific warehouse.
     */
    onClickRequestTransfer(warehouse) {
        const productTemplate = this.props.productTemplate;

        // Resolve product.product ID from the template's variants
        let productId = false;
        const variants = productTemplate.product_variant_ids;
        if (variants) {
            if (Array.isArray(variants) && variants.length > 0) {
                const first = variants[0];
                productId = typeof first === 'object' ? (first.id || false) : first;
            } else if (typeof variants === 'object' && typeof variants[Symbol.iterator] === 'function') {
                // OWL collection/Set — iterate to get first
                for (const v of variants) {
                    productId = typeof v === 'object' ? (v.id || false) : v;
                    break;
                }
            }
        }

        this.dialog.add(TransferRequestPopup, {
            productTemplate: productTemplate,
            productId: productId,
            warehouseName: warehouse.name,
            availableQty: warehouse.free_qty,
            close: () => {},
        });
    },
});
