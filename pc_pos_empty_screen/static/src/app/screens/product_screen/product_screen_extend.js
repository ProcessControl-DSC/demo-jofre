/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    get productsToDisplay() {
        const result = super.productsToDisplay;
        // If no category is actively selected, hide all products
        if (!this.pos.selectedCategory) {
            return [];
        }
        return result;
    },
});
