/** @odoo-module **/

import { PurchaseOrderLineProductField } from
    "@purchase_product_matrix/js/purchase_product_field";
import { useFashionMatrixConfigurator } from
    "@pc_fashion_matrix/js/fashion_matrix_hook";
import { patch } from "@web/core/utils/patch";

/**
 * Patch PurchaseOrderLineProductField to replace the standard
 * matrixConfigurator with our fashion-enhanced version.
 *
 * This makes the enhanced FashionMatrixDialog open automatically
 * when a user selects a product with Color + Size attributes
 * on a purchase order line.
 */
patch(PurchaseOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);
        // Override the matrixConfigurator set in the parent setup()
        // with our fashion-aware version
        this.matrixConfigurator = useFashionMatrixConfigurator();
    },
});
