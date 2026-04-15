/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    get productsToDisplay() {
        let list = [];

        if (this.searchWord !== "") {
            list = this.addMainProductsToDisplay(this.getProductsBySearchWord(this.searchWord));
        } else if (this.pos.selectedCategory?.id) {
            list = this.getProductsByCategory(this.pos.selectedCategory);
        } else {
            return [];
        }

        if (!list || list.length === 0) {
            return [];
        }

        const excludedProductIds = [
            this.pos.config.tip_product_id?.id,
            ...this.pos.hiddenProductIds,
            ...(this.pos.session?._pos_special_products_ids || []),
        ];

        const filteredList = [];
        for (const product of list) {
            if (filteredList.length >= 100) {
                break;
            }
            if (!excludedProductIds.includes(product.id) && product.available_in_pos) {
                filteredList.push(product);
            }
        }

        return this.searchWord !== ""
            ? filteredList
            : filteredList.sort((a, b) => a.display_name.localeCompare(b.display_name));
    },
});
