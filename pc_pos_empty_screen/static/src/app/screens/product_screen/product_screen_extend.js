/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        const updateVisibility = () => this._updateProductVisibility();
        onMounted(updateVisibility);
        onPatched(updateVisibility);
    },

    _updateProductVisibility() {
        const el = this.el || this.__owl__?.bdom?.el;
        if (!el) return;
        const productList = el.querySelector('.product-list');
        if (!productList) return;

        if (this.pos.selectedCategory) {
            productList.style.display = '';
        } else {
            productList.style.display = 'none';
        }
    },
});
