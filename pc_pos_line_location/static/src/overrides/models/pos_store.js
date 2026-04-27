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
     * filtering to locations that currently have stock > 0. Used for
     * outgoing (sale) lines.
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

        const sourceRoot = this.config.picking_type_id?.default_location_src_id;
        const candidates = [];
        for (const loc of this.getCandidateLocations()) {
            if (sourceRoot && !this._isLocationChildOf(loc, sourceRoot)) {
                continue;
            }
            const available = byLocation.get(loc.id);
            if (available && available > 0) {
                candidates.push({ location: loc, available });
            }
        }
        return candidates;
    },

    /**
     * Returns the list of {location, available} for a refund line.
     * The candidates are internal locations under the destination of the
     * return picking type. Stock is shown for information only and does
     * not filter the list (a refund can land in any internal location).
     */
    getReturnLocationCandidatesForProduct(productId) {
        const pickingType = this.config.picking_type_id;
        const returnPickingType =
            pickingType?.return_picking_type_id || pickingType;
        const destRoot = returnPickingType?.default_location_dest_id;
        if (!destRoot) {
            return [];
        }

        const stockByLocation = new Map();
        const quants = this.models["stock.quant"] || [];
        for (const q of quants) {
            if (
                !q.product_id ||
                q.product_id.id !== productId ||
                !q.location_id
            ) {
                continue;
            }
            const prev = stockByLocation.get(q.location_id.id) || 0;
            stockByLocation.set(q.location_id.id, prev + (q.quantity || 0));
        }

        const candidates = [];
        for (const loc of this.getCandidateLocations()) {
            if (!this._isLocationChildOf(loc, destRoot)) {
                continue;
            }
            candidates.push({
                location: loc,
                available: stockByLocation.get(loc.id) || 0,
            });
        }
        return candidates;
    },

    _isLocationChildOf(loc, parent) {
        if (!parent || !loc) {
            return false;
        }
        if (loc.id === parent.id) {
            return true;
        }
        const childPath = loc.parent_path || "";
        const parentPath = parent.parent_path || "";
        return parentPath && childPath.startsWith(parentPath);
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

        const isRefund = line.qty < 0;
        const candidates = isRefund
            ? this.getReturnLocationCandidatesForProduct(product.id)
            : this.getLocationCandidatesForProduct(product.id);

        if (candidates.length === 0) {
            return;
        }

        // Refund quantities are negative; we let the cashier reason in
        // positive numbers and re-apply the sign after the popup closes.
        const totalQty = Math.abs(line.qty);
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

        const sign = isRefund ? -1 : 1;

        if (result.length === 1) {
            this._setLineLocationAndQty(
                line,
                result[0].location,
                sign * result[0].qty
            );
            return;
        }

        // Distribute across multiple lines.
        const order = line.order_id;
        this._setLineLocationAndQty(
            line,
            result[0].location,
            sign * result[0].qty
        );

        for (let i = 1; i < result.length; i++) {
            const alloc = result[i];
            // The core `addLineToOrder` reads `taxes_id` from
            // `vals.product_tmpl_id` (the product.template record), so we
            // must always include it. Passing only `product_id` (the
            // variant) makes `productTemplate` undefined and triggers a
            // TypeError ("Cannot read properties of undefined (reading
            // 'taxes_id')"). We rely on the core to derive `tax_ids` from
            // the template — the sibling line shares product and taxes.
            // `attribute_value_ids` must be passed as x2many command
            // tuples (`[["link", record], ...]`), not as the raw record
            // collection that lives on the source line.
            const attributeValueIds = line.attribute_value_ids
                ? line.attribute_value_ids.map((v) => ["link", v])
                : undefined;
            const newLine = await this.addLineToOrder(
                {
                    product_tmpl_id: product.product_tmpl_id,
                    product_id: product,
                    price_unit: line.price_unit,
                    qty: sign * alloc.qty,
                    discount: line.discount,
                    attribute_value_ids: attributeValueIds,
                    refunded_orderline_id: line.refunded_orderline_id,
                },
                order,
                {},
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
