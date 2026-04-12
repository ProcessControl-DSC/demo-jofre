/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { distributeHund, distributeMatrixToStores } from
    "@pc_fashion_matrix/js/fashion_matrix_distribution";


/**
 * FashionMatrixAction
 *
 * Full-screen client action that renders the enhanced fashion product matrix.
 * Provides a Le New Black-inspired B2B ordering interface with:
 *   - Product image gallery (left panel)
 *   - Color swatches, size x color grid, totals (right panel)
 *   - Store distribution sub-grid (collapsible)
 */
export class FashionMatrixAction extends Component {
    static template = "pc_fashion_matrix.FashionMatrixAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.gridRef = useRef("gridContainer");

        this.state = useState({
            // Loading states
            loading: true,
            loadingProducts: false,

            // Product data
            product: null,
            products: [],
            currentProductIndex: 0,

            // Image gallery
            currentImageIndex: 0,

            // Matrix quantities: {colorId_sizeId: qty}
            quantities: {},

            // Active color filter (null = show all)
            activeColorId: null,

            // Distribution
            showDistribution: false,
            distributionProfiles: [],
            selectedProfileId: null,
            storeDistribution: {},

            // Purchase order context
            purchaseOrderId: null,
            seasonId: null,
            gender: null,
            partnerId: null,
            distributionProfileId: null,

            // Products search / filter
            searchQuery: "",
        });

        onWillStart(async () => {
            await this._loadInitialData();
        });

        onMounted(() => {
            // Focus first input if grid is visible
            this._focusFirstInput();
        });
    }

    // -------------------------------------------------------------------------
    // DATA LOADING
    // -------------------------------------------------------------------------

    async _loadInitialData() {
        const params = this.props.action.params || {};
        this.state.purchaseOrderId = params.purchase_order_id || null;
        this.state.seasonId = params.season_id || null;
        this.state.gender = params.gender || null;
        this.state.partnerId = params.partner_id || null;
        this.state.distributionProfileId = params.distribution_profile_id || null;

        // Load distribution profiles
        this.state.distributionProfiles = await this.orm.call(
            "product.template",
            "_get_distribution_profiles",
            [],
        );

        if (this.state.distributionProfileId) {
            this.state.selectedProfileId = this.state.distributionProfileId;
        }

        // Load products for this supplier/season/gender combination
        await this._loadProducts();

        this.state.loading = false;
    }

    async _loadProducts() {
        this.state.loadingProducts = true;

        // Build domain to find fashion products
        const domain = [
            ["attribute_line_ids", "!=", false],
        ];

        if (this.state.partnerId) {
            domain.push(["seller_ids.partner_id", "=", this.state.partnerId]);
        }
        if (this.state.seasonId) {
            domain.push(["fashion_season_id", "=", this.state.seasonId]);
        }
        if (this.state.gender) {
            domain.push(["fashion_gender", "=", this.state.gender]);
        }

        const templateIds = await this.orm.searchRead(
            "product.template",
            domain,
            ["id", "name", "default_code", "list_price", "image_128"],
            { limit: 200, order: "name asc" },
        );

        this.state.products = templateIds;

        // Load first product if available
        if (this.state.products.length > 0) {
            await this._loadProductDetail(this.state.products[0].id);
            this.state.currentProductIndex = 0;
        }

        this.state.loadingProducts = false;
    }

    async _loadProductDetail(productTemplateId) {
        this.state.loading = true;
        const data = await this.orm.call(
            "product.template",
            "_get_fashion_matrix_data",
            [productTemplateId],
        );
        this.state.product = data;
        this.state.currentImageIndex = 0;
        this.state.activeColorId = null;
        // Reset quantities for this product
        this.state.quantities = {};
        if (data.colors && data.sizes) {
            for (const color of data.colors) {
                for (const size of data.sizes) {
                    const key = `${color.id}_${size.id}`;
                    this.state.quantities[key] = 0;
                }
            }
        }
        // Recalculate distribution
        this._recalculateDistribution();
        this.state.loading = false;
    }

    // -------------------------------------------------------------------------
    // PRODUCT NAVIGATION
    // -------------------------------------------------------------------------

    get filteredProducts() {
        if (!this.state.searchQuery) {
            return this.state.products;
        }
        const query = this.state.searchQuery.toLowerCase();
        return this.state.products.filter(p =>
            (p.name || "").toLowerCase().includes(query) ||
            (p.default_code || "").toLowerCase().includes(query)
        );
    }

    async onSelectProduct(productId) {
        const idx = this.state.products.findIndex(p => p.id === productId);
        if (idx >= 0) {
            this.state.currentProductIndex = idx;
            await this._loadProductDetail(productId);
        }
    }

    async onNextProduct() {
        if (this.state.currentProductIndex < this.state.products.length - 1) {
            this.state.currentProductIndex++;
            await this._loadProductDetail(
                this.state.products[this.state.currentProductIndex].id
            );
        }
    }

    async onPrevProduct() {
        if (this.state.currentProductIndex > 0) {
            this.state.currentProductIndex--;
            await this._loadProductDetail(
                this.state.products[this.state.currentProductIndex].id
            );
        }
    }

    onSearchProducts(ev) {
        this.state.searchQuery = ev.target.value;
    }

    // -------------------------------------------------------------------------
    // IMAGE GALLERY
    // -------------------------------------------------------------------------

    get currentImage() {
        const p = this.state.product;
        if (!p || !p.images || p.images.length === 0) {
            return null;
        }
        return p.images[this.state.currentImageIndex] || p.images[0];
    }

    onPrevImage() {
        if (this.state.currentImageIndex > 0) {
            this.state.currentImageIndex--;
        } else if (this.state.product && this.state.product.images) {
            this.state.currentImageIndex = this.state.product.images.length - 1;
        }
    }

    onNextImage() {
        const images = this.state.product ? this.state.product.images : [];
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
            this.state.activeColorId = null; // Toggle off
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
        const key = `${colorId}_${sizeId}`;
        return this.state.quantities[key] || 0;
    }

    onQtyChange(colorId, sizeId, ev) {
        const key = `${colorId}_${sizeId}`;
        const val = parseInt(ev.target.value, 10);
        this.state.quantities[key] = isNaN(val) || val < 0 ? 0 : val;
        this._recalculateDistribution();
    }

    onQtyKeydown(colorId, sizeId, ev) {
        const key = `${colorId}_${sizeId}`;
        let current = this.state.quantities[key] || 0;

        if (ev.key === "ArrowUp") {
            ev.preventDefault();
            this.state.quantities[key] = current + 1;
            ev.target.value = this.state.quantities[key];
            this._recalculateDistribution();
        } else if (ev.key === "ArrowDown") {
            ev.preventDefault();
            this.state.quantities[key] = Math.max(0, current - 1);
            ev.target.value = this.state.quantities[key];
            this._recalculateDistribution();
        } else if (ev.key === "Tab" || ev.key === "Enter") {
            // Allow default tab behavior for grid navigation
        }
    }

    // Row total (sum for a color across all sizes)
    getRowTotal(colorId) {
        const p = this.state.product;
        if (!p || !p.sizes) return 0;
        let total = 0;
        for (const size of p.sizes) {
            total += this.getQty(colorId, size.id);
        }
        return total;
    }

    // Column total (sum for a size across all visible colors)
    getColTotal(sizeId) {
        let total = 0;
        for (const color of this.visibleColors) {
            total += this.getQty(color.id, sizeId);
        }
        return total;
    }

    // Grand total units
    get grandTotalUnits() {
        const p = this.state.product;
        if (!p) return 0;
        let total = 0;
        for (const key of Object.keys(this.state.quantities)) {
            total += this.state.quantities[key] || 0;
        }
        return total;
    }

    // Grand total at list price (PVP)
    get grandTotalPVP() {
        const p = this.state.product;
        if (!p) return 0;
        return this.grandTotalUnits * (p.list_price || 0);
    }

    // Grand total at cost price
    get grandTotalCost() {
        const p = this.state.product;
        if (!p) return 0;
        const costPrice = p.seller_price || p.standard_price || 0;
        return this.grandTotalUnits * costPrice;
    }

    // Margin percentage
    get marginPercent() {
        if (this.grandTotalPVP === 0) return 0;
        return ((this.grandTotalPVP - this.grandTotalCost) / this.grandTotalPVP) * 100;
    }

    // Format currency
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
    // STORE DISTRIBUTION
    // -------------------------------------------------------------------------

    toggleDistribution() {
        this.state.showDistribution = !this.state.showDistribution;
        if (this.state.showDistribution) {
            this._recalculateDistribution();
        }
    }

    onSelectProfile(ev) {
        const profileId = parseInt(ev.target.value, 10);
        this.state.selectedProfileId = profileId || null;
        this._recalculateDistribution();
    }

    get selectedProfile() {
        if (!this.state.selectedProfileId) return null;
        return this.state.distributionProfiles.find(
            p => p.id === this.state.selectedProfileId
        ) || null;
    }

    _recalculateDistribution() {
        const profile = this.selectedProfile;
        if (!profile || !this.state.product) {
            this.state.storeDistribution = {};
            return;
        }

        // Build matrix quantities as {colorId: {sizeId: qty}}
        const matrixQtys = {};
        const p = this.state.product;
        for (const color of (p.colors || [])) {
            matrixQtys[color.id] = {};
            for (const size of (p.sizes || [])) {
                matrixQtys[color.id][size.id] = this.getQty(color.id, size.id);
            }
        }

        const storePercentages = profile.lines.map(l => ({
            warehouseId: l.warehouse_id,
            warehouseName: l.warehouse_name,
            percentage: l.percentage,
        }));

        this.state.storeDistribution = distributeMatrixToStores(
            matrixQtys, storePercentages
        );
    }

    getStoreQty(warehouseId, colorId, sizeId) {
        const dist = this.state.storeDistribution;
        if (!dist || !dist[warehouseId] || !dist[warehouseId][colorId]) return 0;
        return dist[warehouseId][colorId][sizeId] || 0;
    }

    getStoreTotalForSize(warehouseId, sizeId) {
        const profile = this.selectedProfile;
        if (!profile || !this.state.product) return 0;
        let total = 0;
        for (const color of (this.state.product.colors || [])) {
            total += this.getStoreQty(warehouseId, color.id, sizeId);
        }
        return total;
    }

    getStoreTotalForColor(warehouseId, colorId) {
        const profile = this.selectedProfile;
        if (!profile || !this.state.product) return 0;
        let total = 0;
        for (const size of (this.state.product.sizes || [])) {
            total += this.getStoreQty(warehouseId, colorId, size.id);
        }
        return total;
    }

    getStoreGrandTotal(warehouseId) {
        const profile = this.selectedProfile;
        if (!profile || !this.state.product) return 0;
        let total = 0;
        for (const color of (this.state.product.colors || [])) {
            for (const size of (this.state.product.sizes || [])) {
                total += this.getStoreQty(warehouseId, color.id, size.id);
            }
        }
        return total;
    }

    // -------------------------------------------------------------------------
    // ACTIONS
    // -------------------------------------------------------------------------

    async onConfirm() {
        const p = this.state.product;
        if (!p || this.grandTotalUnits === 0) {
            this.notification.add(
                _t("Please enter quantities before confirming."),
                { type: "warning" }
            );
            return;
        }

        if (!this.state.purchaseOrderId) {
            this.notification.add(
                _t("No purchase order context. Cannot add lines."),
                { type: "danger" }
            );
            return;
        }

        // Build order lines from the matrix
        const linesToCreate = [];
        for (const color of p.colors) {
            for (const size of p.sizes) {
                const qty = this.getQty(color.id, size.id);
                if (qty > 0) {
                    const variantKey = `${color.id}_${size.id}`;
                    const variantInfo = p.variant_map[variantKey];
                    if (variantInfo) {
                        linesToCreate.push({
                            product_id: variantInfo.product_id,
                            product_qty: qty,
                        });
                    }
                }
            }
        }

        if (linesToCreate.length === 0) {
            this.notification.add(
                _t("No valid product variants found for the entered quantities."),
                { type: "warning" }
            );
            return;
        }

        // Call server method to add lines to the PO
        try {
            await this.orm.call(
                "purchase.order",
                "action_fashion_matrix_add_lines",
                [this.state.purchaseOrderId, linesToCreate],
            );
            this.notification.add(
                _t("%s lines added to the purchase order.", linesToCreate.length),
                { type: "success" }
            );

            // Move to next product or go back
            if (this.state.currentProductIndex < this.state.products.length - 1) {
                await this.onNextProduct();
            } else {
                this.onGoBack();
            }
        } catch (error) {
            this.notification.add(
                _t("Error adding lines: ") + (error.message || error.data?.message || "Unknown error"),
                { type: "danger" }
            );
        }
    }

    onSkip() {
        if (this.state.currentProductIndex < this.state.products.length - 1) {
            this.onNextProduct();
        } else {
            this.onGoBack();
        }
    }

    onGoBack() {
        if (this.state.purchaseOrderId) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "purchase.order",
                res_id: this.state.purchaseOrderId,
                views: [[false, "form"]],
                target: "current",
            });
        } else {
            this.action.doAction({ type: "ir.actions.act_window_close" });
        }
    }

    onClearAll() {
        for (const key of Object.keys(this.state.quantities)) {
            this.state.quantities[key] = 0;
        }
        this._recalculateDistribution();
    }

    // -------------------------------------------------------------------------
    // HELPERS
    // -------------------------------------------------------------------------

    _focusFirstInput() {
        const container = this.gridRef.el;
        if (container) {
            const firstInput = container.querySelector(
                ".o_fashion_matrix_cell input"
            );
            if (firstInput) {
                firstInput.focus();
                firstInput.select();
            }
        }
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

    get costPrice() {
        const p = this.state.product;
        if (!p) return 0;
        return p.seller_price || p.standard_price || 0;
    }

    get marginClass() {
        const m = this.marginPercent;
        if (m >= 50) return "text-success fw-bold";
        if (m >= 30) return "text-primary";
        if (m >= 15) return "text-warning";
        return "text-danger fw-bold";
    }

    get productCounter() {
        const total = this.state.products.length;
        const current = this.state.currentProductIndex + 1;
        return `${current} / ${total}`;
    }
}

// Register the client action
registry.category("actions").add(
    "pc_fashion_matrix.open_fashion_matrix",
    FashionMatrixAction
);


// Also register the method on purchase.order to add lines from the matrix
// This needs a corresponding Python method:

