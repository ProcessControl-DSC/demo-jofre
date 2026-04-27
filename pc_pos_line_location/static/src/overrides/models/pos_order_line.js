import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { getPosStore } from "@pc_pos_line_location/overrides/models/pos_store";

patch(PosOrderline.prototype, {
    setQuantity(quantity, keep_price) {
        const previousQty = this.qty;
        const result = super.setQuantity(quantity, keep_price);

        // If super returned a UserError-like dict (refund validation), don't reprompt.
        if (result && typeof result === "object" && result.title) {
            return result;
        }

        if (this.uiState?.skipLocationPrompt) {
            return result;
        }

        const pos = getPosStore();
        if (!pos || !pos.config?.allow_line_location_selection) {
            return result;
        }

        if (!this.location_id) {
            return result;
        }

        if (this.qty === previousQty || this.qty <= 0) {
            return result;
        }

        const productId = this.product_id?.id;
        if (!productId) {
            return result;
        }

        const candidates = pos.getLocationCandidatesForProduct(productId);
        if (candidates.length <= 1) {
            return result;
        }

        // Re-open popup asynchronously to let the current call resolve.
        Promise.resolve().then(() => pos.promptLineLocation(this));
        return result;
    },
});
