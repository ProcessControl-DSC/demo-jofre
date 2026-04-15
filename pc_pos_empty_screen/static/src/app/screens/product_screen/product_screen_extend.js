/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    get productsToDisplay() {
        // If no category selected and no search, show nothing
        if (!this.pos.selectedCategory?.id && !this.searchWord) {
            return [];
        }
        return super.productsToDisplay;
    },
});
