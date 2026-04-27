import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { SelectLocationPopup } from "@pc_pos_line_location/app/popups/select_location_popup";

let _posStore = null;

export function getPosStore() {
    return _posStore;
}

patch(PosStore.prototype, {
    async setup(...args) {
        const result = await super.setup(...args);
        _posStore = this;
        return result;
    },

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

    /**
     * Open the popup to allocate the line quantity across one or more
     * source locations. If the user assigns to a single location, the
     * existing line is updated. If the user splits across N locations,
     * the existing line keeps the first allocation and N-1 sibling
     * lines are created with the remaining allocations.
     */
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

        const totalQty = line.qty;
        if (candidates.length === 1) {
            this._setLineLocation(line, candidates[0].location);
            return;
        }

        const initialAllocations = {};
        if (line.location_id) {
            initialAllocations[line.location_id.id] = totalQty;
        }

        const result = await makeAwaitable(this.dialog, SelectLocationPopup, {
            title: undefined,
            productName: product.display_name,
            totalQty,
            candidates,
            initialAllocations: Object.keys(initialAllocations).length
                ? initialAllocations
                : null,
        });
        if (!result || result.length === 0) {
            return;
        }

        if (result.length === 1) {
            this._setLineLocationAndQty(line, result[0].location, result[0].qty);
            return;
        }

        // Distribute across multiple lines.
        const order = line.order_id;
        this._setLineLocationAndQty(line, result[0].location, result[0].qty);

        for (let i = 1; i < result.length; i++) {
            const alloc = result[i];
            const newLine = await this.addLineToOrder(
                {
                    product_id: product,
                    price_unit: line.price_unit,
                    qty: alloc.qty,
                    discount: line.discount,
                    tax_ids: line.tax_ids,
                    attribute_value_ids: line.attribute_value_ids,
                },
                order,
                { merge: false },
                false
            );
            if (newLine) {
                this._setLineLocation(newLine, alloc.location);
            }
        }
    },

    _setLineLocation(line, location) {
        if (!line) {
            return;
        }
        line.uiState = line.uiState || {};
        line.uiState.skipLocationPrompt = true;
        try {
            line.update({ location_id: location });
        } finally {
            line.uiState.skipLocationPrompt = false;
        }
    },

    _setLineLocationAndQty(line, location, qty) {
        if (!line) {
            return;
        }
        line.uiState = line.uiState || {};
        line.uiState.skipLocationPrompt = true;
        try {
            line.update({ location_id: location });
            if (qty !== undefined && qty !== line.qty) {
                line.setQuantity(qty);
            }
        } finally {
            line.uiState.skipLocationPrompt = false;
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
