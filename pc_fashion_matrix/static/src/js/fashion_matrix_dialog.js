/** @odoo-module **/

import { Component, useState, onMounted, onWillStart, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

/**
 * FashionMatrixDialog
 *
 * Enhanced product matrix dialog that replaces the standard ProductMatrixDialog
 * when a product has fashion attributes (Color + Size).
 *
 * Layout:
 *   - Left panel (~40%): Large product image with gallery navigation
 *   - Right panel (~60%): Product info, color swatches, size x color grid
 *     with quantity inputs, row/column/grand totals
 *
 * Data flow:
 *   Receives the same props as ProductMatrixDialog (header, rows, etc.)
 *   plus additional fashion data fetched via RPC (get_fashion_matrix_data).
 *   On confirm, writes back to the record using the standard grid/grid_update
 *   mechanism so the server creates order lines normally.
 */
export class FashionMatrixDialog extends Component {
    static template = "pc_fashion_matrix.FashionMatrixDialog";
    static props = {
        header: { type: Object },
        rows: { type: Object },
        editedCellAttributes: { type: String },
        product_template_id: { type: Number },
        record: { type: Object },
        close: { type: Function },
    };
    static components = { Dialog };

    setup() {
        this.orm = useService("orm");
        this.size = "fullscreen";

        this.matrixRef = useRef("fashionMatrix");

        this.state = useState({
            loading: true,
            // Fashion data from RPC
            product: null,
            // Image gallery
            currentImageIndex: 0,
            // Active color filter (null = show all)
            activeColorId: null,
            // Quantities: { "colorId_sizeId": qty }
            quantities: {},
        });

        // Parse the standard matrix rows to build our initial quantities
        this._parseMatrixRows();

        useHotkey("enter", () => this._onConfirm(), {
            bypassEditableProtection: true,
            area: () => this.matrixRef.el,
        });

        onWillStart(async () => {
            await this._loadFashionData();
        });

        onMounted(() => {
            this._focusFirstInput();
        });
    }

    // -------------------------------------------------------------------------
    // DATA LOADING
    // -------------------------------------------------------------------------

    /**
     * Parse the standard Odoo matrix rows to extract initial quantities.
     * The standard matrix structure is:
     *   rows = [ [rowHeader, cell1, cell2, ...], ... ]
     * Each cell has: { ptav_ids, qty, is_possible_combination, ... }
     */
    _parseMatrixRows() {
        // We do not pre-fill from standard rows here; we will build our own
        // grid from fashion data. The standard rows are kept for the confirm
        // action which writes back using ptav_ids.
        this._standardRows = this.props.rows;
        this._standardHeader = this.props.header;
    }

    /**
     * Cross-reference the standard matrix data with fashion data to
     * pre-fill quantities that were already on the order.
     */
    _initQuantitiesFromMatrix(fashionData) {
        if (!fashionData || !fashionData.colors || !fashionData.sizes) {
            return;
        }
        // Initialize all cells to 0
        for (const color of fashionData.colors) {
            for (const size of fashionData.sizes) {
                const key = `${color.id}_${size.id}`;
                this.state.quantities[key] = 0;
            }
        }

        // Try to map standard matrix quantities to our color/size grid
        // The standard matrix cells have ptav_ids (product template attribute value ids)
        // We need to map those to our color.id / size.id (product attribute value ids)
        // Build a reverse map: ptav_ids string -> {colorId, sizeId}
        if (!this._standardRows) return;

        // Build ptav -> attribute value mapping from variant_map
        // variant_map keys are "colorValId_sizeValId" -> { product_id, ... }
        // We need to also map ptav_ids from the matrix to color/size value ids.
        // The standard matrix cells contain ptav_ids as comma-separated template attr value ids.
        // We'll match by iterating standard rows and extracting qty for each cell.
        for (const row of this._standardRows) {
            for (const cell of row) {
                if (cell.ptav_ids && cell.is_possible_combination && cell.qty) {
                    const qty = parseFloat(cell.qty) || 0;
                    if (qty > 0) {
                        // Try to find matching color/size from the fashion data variant map
                        const ptavIds = (Array.isArray(cell.ptav_ids) ? cell.ptav_ids : String(cell.ptav_ids).split(",").map(id => parseInt(id))).sort((a, b) => a - b);
                        const matchKey = this._findVariantByPtavIds(fashionData, ptavIds);
                        if (matchKey) {
                            this.state.quantities[matchKey] = qty;
                        }
                    }
                }
            }
        }
    }

    /**
     * Find the color_size key that matches the given ptav_ids.
     * This requires matching product template attribute value ids back
     * to product attribute value ids via the variant map.
     */
    _findVariantByPtavIds(fashionData, ptavIds) {
        // We will brute-force match: for each variant in variant_map,
        // get the product.product, and compare its ptav_ids.
        // Since we don't have ptav data directly, we'll store a lookup
        // built during _loadFashionData.
        // For now, the simplest approach: if quantities were 0 (new line),
        // we don't need to pre-fill. If editing, the matrix already has qtys.
        // This is a best-effort match.
        return null;
    }

    // -------------------------------------------------------------------------
    // IMAGE GALLERY
    // -------------------------------------------------------------------------

    get currentImage() {
        const p = this.state.product;
        if (!p || !p.images || p.images.length === 0) return null;
        return p.images[this.state.currentImageIndex] || p.images[0];
    }

    get hasMultipleImages() {
        return this.state.product && this.state.product.images && this.state.product.images.length > 1;
    }

    onPrevImage() {
        const images = this.state.product ? this.state.product.images : [];
        if (images.length <= 1) return;
        if (this.state.currentImageIndex > 0) {
            this.state.currentImageIndex--;
        } else {
            this.state.currentImageIndex = images.length - 1;
        }
    }

    onNextImage() {
        const images = this.state.product ? this.state.product.images : [];
        if (images.length <= 1) return;
        if (this.state.currentImageIndex < images.length - 1) {
            this.state.currentImageIndex++;
        } else {
            this.state.currentImageIndex = 0;
        }
    }

    onSelectThumbnail(index) {
        this.state.currentImageIndex = index;
    }

    // -------------------------------------------------------------------------
    // COLOR SWATCHES
    // -------------------------------------------------------------------------

    onSelectColor(colorId) {
        if (this.state.activeColorId === colorId) {
            this.state.activeColorId = null;
        } else {
            this.state.activeColorId = colorId;
        }
    }

    get visibleColors() {
        const p = this.state.product;
        if (!p || !p.colors) return [];
        if (this.state.activeColorId) {
            return p.colors.filter(c => c.id === this.state.activeColorId);
        }
        return p.colors;
    }

    // -------------------------------------------------------------------------
    // MATRIX QUANTITIES
    // -------------------------------------------------------------------------

    getQty(colorId, sizeId) {
        return this.state.quantities[`${colorId}_${sizeId}`] || 0;
    }

    onQtyChange(colorId, sizeId, ev) {
        const key = `${colorId}_${sizeId}`;
        const val = parseInt(ev.target.value, 10);
        this.state.quantities[key] = isNaN(val) || val < 0 ? 0 : val;
    }

    onQtyKeydown(colorId, sizeId, ev) {
        const key = `${colorId}_${sizeId}`;
        let current = this.state.quantities[key] || 0;

        if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this.state.quantities[key] = current + 1;
            ev.target.value = this.state.quantities[key];
        } else if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.state.quantities[key] = Math.max(0, current - 1);
            ev.target.value = this.state.quantities[key];
        }
    }

    getRowTotal(colorId) {
        const p = this.state.product;
        if (!p || !p.sizes) return 0;
        let total = 0;
        for (const size of p.sizes) {
            total += this.getQty(colorId, size.id);
        }
        return total;
    }

    getColTotal(sizeId) {
        let total = 0;
        for (const color of this.visibleColors) {
            total += this.getQty(color.id, sizeId);
        }
        return total;
    }

    get grandTotalUnits() {
        const p = this.state.product;
        if (!p) return 0;
        let total = 0;
        for (const key of Object.keys(this.state.quantities)) {
            total += this.state.quantities[key] || 0;
        }
        return total;
    }

    get grandTotalPVP() {
        const p = this.state.product;
        if (!p) return 0;
        return this.grandTotalUnits * (p.list_price || 0);
    }

    get grandTotalCost() {
        const p = this.state.product;
        if (!p) return 0;
        return this.grandTotalUnits * this.costPrice;
    }

    get costPrice() {
        const p = this.state.product;
        if (!p) return 0;
        return p.seller_price || p.standard_price || 0;
    }

    get marginPercent() {
        if (this.grandTotalPVP === 0) return 0;
        return ((this.grandTotalPVP - this.grandTotalCost) / this.grandTotalPVP) * 100;
    }

    get marginClass() {
        const m = this.marginPercent;
        if (m >= 50) return "text-success fw-bold";
        if (m >= 30) return "text-primary";
        if (m >= 15) return "text-warning";
        return "text-danger fw-bold";
    }

    get unitMarginPercent() {
        const p = this.state.product;
        if (!p || !p.list_price) return 0;
        return ((p.list_price - this.costPrice) / p.list_price * 100);
    }

    get genderBadgeClass() {
        const g = this.state.product?.gender;
        const map = {
            man: "bg-primary",
            woman: "bg-danger",
            boy: "bg-info",
            girl: "bg-warning",
            baby: "bg-success",
            unisex: "bg-secondary",
        };
        return map[g] || "bg-secondary";
    }

    formatCurrency(value) {
        const p = this.state.product;
        if (!p) return value.toFixed(2);
        const symbol = p.currency_symbol || "\u20ac";
        const position = p.currency_position || "after";
        const formatted = value.toFixed(2);
        if (position === "before") {
            return `${symbol}${formatted}`;
        }
        return `${formatted} ${symbol}`;
    }

    // -------------------------------------------------------------------------
    // ACTIONS
    // -------------------------------------------------------------------------

    /**
     * Confirm: Build the matrix changes in the standard Odoo format
     * (ptav_ids + qty) and write them back to the record using grid/grid_update.
     * This ensures full compatibility with the standard purchase/sale matrix flow.
     */
    _onConfirm() {
        const p = this.state.product;
        if (!p || !p.variant_map) {
            this.props.close();
            return;
        }

        const matrixChanges = [];

        // For each cell with quantity > 0, find the matching ptav_ids
        // from the standard matrix rows
        for (const color of (p.colors || [])) {
            for (const size of (p.sizes || [])) {
                const qty = this.getQty(color.id, size.id);
                if (qty > 0) {
                    // Find matching ptav_ids from standard rows
                    const ptavIds = this._findPtavIds(color.id, size.id);
                    if (ptavIds && ptavIds.length > 0) {
                        matrixChanges.push({
                            qty: qty,
                            ptav_ids: ptavIds,
                        });
                    }
                }
            }
        }

        if (matrixChanges.length > 0) {
            this.props.record.update({
                grid: JSON.stringify({
                    changes: matrixChanges,
                    product_template_id: this.props.product_template_id,
                }),
                grid_update: true,
            });
        }
        this.props.close();
    }

    /**
     * Find the ptav_ids (product template attribute value IDs) for a given
     * color/size combination by scanning the standard matrix rows.
     *
     * The standard matrix cells have ptav_ids as comma-separated strings.
     * We need to find the cell whose combination matches our color + size.
     */
    _findPtavIds(colorId, sizeId) {
        if (!this._standardRows) return null;

        // Build lookup from variant_map: colorId_sizeId -> product_id
        const variantKey = `${colorId}_${sizeId}`;
        const variantInfo = this.state.product?.variant_map?.[variantKey];
        if (!variantInfo) return null;

        // Scan all standard matrix cells to find one matching this combination
        for (const row of this._standardRows) {
            for (const cell of row) {
                if (cell.ptav_ids && cell.is_possible_combination) {
                    // The ptav_ids in the cell correspond to the variant's
                    // product_template_attribute_value_ids. We match by checking
                    // if this cell's combination maps to the same product variant.
                    // Store the ptav_ids for each cell
                    const ptavIds = Array.isArray(cell.ptav_ids) ? cell.ptav_ids : String(cell.ptav_ids).split(",").map(id => parseInt(id));
                    // Check if this cell was already populated with this color/size
                    // We'll use a heuristic: try all cells and see which one
                    // maps to the correct variant by matching ptav names/values.
                    // Since we need to be efficient, store ptavIds per cell and
                    // match against the variant map during load.
                    // For now, collect all ptav_ids and check against product variant
                    if (this._ptavMatchesVariant(ptavIds, colorId, sizeId)) {
                        return ptavIds;
                    }
                }
            }
        }
        return null;
    }

    /**
     * Check if a set of ptav_ids corresponds to a variant with the given
     * color and size attribute values.
     *
     * We use the _ptavToVariant map built during initialization.
     */
    _ptavMatchesVariant(ptavIds, colorId, sizeId) {
        // If we have a pre-built map, use it
        if (this._ptavMap) {
            const key = ptavIds.sort((a, b) => a - b).join(",");
            const mapped = this._ptavMap[key];
            if (mapped) {
                return mapped.colorId === colorId && mapped.sizeId === sizeId;
            }
        }
        return false;
    }

    /**
     * Build the ptav -> color/size mapping by cross-referencing
     * the standard matrix data with the fashion data.
     *
     * Called after fashion data is loaded so we can do a server call
     * to resolve ptav_ids to attribute value ids.
     */
    async _buildPtavMap() {
        this._ptavMap = {};
        if (!this._standardRows || !this.state.product) return;

        // Collect all unique ptav_ids from the matrix
        const allPtavSets = [];
        for (const row of this._standardRows) {
            for (const cell of row) {
                if (cell.ptav_ids && cell.is_possible_combination) {
                    const ptavIds = (Array.isArray(cell.ptav_ids) ? cell.ptav_ids : String(cell.ptav_ids).split(",").map(id => parseInt(id))).sort((a, b) => a - b);
                    allPtavSets.push(ptavIds);
                }
            }
        }

        if (allPtavSets.length === 0) return;

        // Fetch all ptav records to get their product_attribute_value_id
        const allPtavIds = [...new Set(allPtavSets.flat())];
        try {
            const ptavRecords = await this.orm.searchRead(
                "product.template.attribute.value",
                [["id", "in", allPtavIds]],
                ["id", "product_attribute_value_id", "attribute_id"],
            );

            // Build ptav_id -> { attribute_value_id, attribute_id }
            const ptavLookup = {};
            for (const rec of ptavRecords) {
                ptavLookup[rec.id] = {
                    valueId: rec.product_attribute_value_id[0],
                    attrId: rec.attribute_id[0],
                };
            }

            // Determine which attribute is color and which is size
            const p = this.state.product;
            const colorValueIds = new Set((p.colors || []).map(c => c.id));
            const sizeValueIds = new Set((p.sizes || []).map(s => s.id));

            // For each ptav combination, determine color and size
            for (const ptavIds of allPtavSets) {
                let colorId = null;
                let sizeId = null;
                for (const ptavId of ptavIds) {
                    const info = ptavLookup[ptavId];
                    if (!info) continue;
                    if (colorValueIds.has(info.valueId)) {
                        colorId = info.valueId;
                    } else if (sizeValueIds.has(info.valueId)) {
                        sizeId = info.valueId;
                    }
                }
                if (colorId && sizeId) {
                    const key = ptavIds.join(",");
                    this._ptavMap[key] = { colorId, sizeId };
                }
            }
        } catch (e) {
            console.error("FashionMatrixDialog: Error building ptav map", e);
        }
    }

    _onDiscard() {
        this.props.close();
    }

    onClearAll() {
        for (const key of Object.keys(this.state.quantities)) {
            this.state.quantities[key] = 0;
        }
    }

    // -------------------------------------------------------------------------
    // DATA LOADING (main entry point, called from onWillStart)
    // -------------------------------------------------------------------------

    async _loadFashionData() {
        try {
            const data = await this.orm.call(
                "product.template",
                "get_fashion_matrix_data",
                [this.props.product_template_id],
            );
            this.state.product = data;
            this._initQuantitiesFromMatrix(data);

            // Build the ptav -> color/size mapping for the confirm action
            await this._buildPtavMap();

            // Now re-init quantities using the ptav map for editing scenarios
            this._reinitQuantitiesWithPtavMap(data);

            this.state.loading = false;
        } catch (e) {
            console.error("FashionMatrixDialog: Error loading fashion data", e);
            this.state.loading = false;
        }
    }

    /**
     * Re-initialize quantities using the ptav map to correctly map
     * existing matrix quantities to our color/size grid.
     */
    _reinitQuantitiesWithPtavMap(fashionData) {
        if (!this._ptavMap || !this._standardRows || !fashionData) return;

        for (const row of this._standardRows) {
            for (const cell of row) {
                if (cell.ptav_ids && cell.is_possible_combination && cell.qty) {
                    const qty = parseFloat(cell.qty) || 0;
                    if (qty > 0) {
                        const ptavIds = (Array.isArray(cell.ptav_ids) ? cell.ptav_ids : String(cell.ptav_ids).split(",").map(id => parseInt(id))).sort((a, b) => a - b);
                        const key = ptavIds.join(",");
                        const mapped = this._ptavMap[key];
                        if (mapped) {
                            const qtyKey = `${mapped.colorId}_${mapped.sizeId}`;
                            this.state.quantities[qtyKey] = qty;
                        }
                    }
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // HELPERS
    // -------------------------------------------------------------------------

    _focusFirstInput() {
        const container = this.matrixRef.el;
        if (container) {
            const firstInput = container.querySelector(".o_fashion_matrix_input");
            if (firstInput) {
                firstInput.focus();
                firstInput.select();
            }
        }
    }
}
