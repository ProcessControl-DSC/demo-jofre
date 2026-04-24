import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { SelectLocationPopup } from "@pc_pos_line_location/app/popups/select_location_popup";

patch(PosStore.prototype, {
    /**
     * Candidate internal locations loaded in this POS session.
     * Children of the picking type source location with usage 'internal'.
     */
    getCandidateLocations() {
        return this.models["stock.location"]
            ? this.models["stock.location"].filter((l) => l.usage === "internal")
            : [];
    },

    /**
     * Returns the list of {location, available} for a given product,
     * filtering to locations that currently have stock > 0.
     */
    getLocationCandidatesForProduct(productId) {
        const quants = this.models["stock.quant"]
            ? this.models["stock.quant"].filter(
                  (q) =>
                      q.product_id &&
                      q.product_id.id === productId &&
                      q.quantity > 0
              )
            : [];

        const byLocation = new Map();
        for (const q of quants) {
            if (!q.location_id) {
                continue;
            }
            const locId = q.location_id.id;
            const prev = byLocation.get(locId) || 0;
            byLocation.set(locId, prev + q.quantity - (q.reserved_quantity || 0));
        }

        const candidates = [];
        for (const loc of this.getCandidateLocations()) {
            const available = byLocation.get(loc.id);
            if (available && available > 0) {
                candidates.push({ location: loc, available });
            }
        }
        return candidates;
    },

    async promptLineLocation(line) {
        if (!this.config.allow_line_location_selection) {
            return;
        }
        const product = line.product_id;
        if (!product || product.type !== "consu" || !product.is_storable) {
            return;
        }
        const candidates = this.getLocationCandidatesForProduct(product.id);

        if (candidates.length === 0) {
            return;
        }
        if (candidates.length === 1) {
            line.update({ location_id: candidates[0].location });
            return;
        }

        const chosen = await makeAwaitable(this.dialog, SelectLocationPopup, {
            title: undefined,
            productName: product.display_name,
            candidates: candidates,
        });
        if (chosen) {
            line.update({ location_id: chosen });
        }
    },

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        const line = await super.addLineToOrder(vals, order, opts, configure);
        if (configure && line && !line.location_id) {
            await this.promptLineLocation(line);
        }
        return line;
    },
});
