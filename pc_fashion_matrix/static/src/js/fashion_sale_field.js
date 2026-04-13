/** @odoo-module **/

import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { useFashionMatrixConfigurator } from
    "@pc_fashion_matrix/js/fashion_matrix_hook";
import { patch } from "@web/core/utils/patch";

/**
 * Patch SaleOrderLineProductField to replace the standard
 * matrixConfigurator with our fashion-enhanced version.
 *
 * The sale_product_matrix module already patches SaleOrderLineProductField
 * to add this.matrixConfigurator. We patch again to replace it with
 * our fashion-aware version.
 *
 * This makes the enhanced FashionMatrixDialog open automatically
 * when a user selects a product with Color + Size attributes
 * on a sale order line.
 */
patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);
        // Override the matrixConfigurator set by sale_product_matrix's patch
        // with our fashion-aware version
        this.matrixConfigurator = useFashionMatrixConfigurator();
    },
});
