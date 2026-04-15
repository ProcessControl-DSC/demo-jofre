/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this._transferCache = [];
    },

    /**
     * Get the warehouse_id from the current POS config.
     * @returns {number|false}
     */
    getTransferWarehouseId() {
        const warehouseId = this.config.warehouse_id;
        if (warehouseId) {
            return warehouseId.id || warehouseId;
        }
        // Fallback: try picking_type_id.warehouse_id
        const pickingType = this.config.picking_type_id;
        if (pickingType && pickingType.warehouse_id) {
            return pickingType.warehouse_id.id || pickingType.warehouse_id;
        }
        return false;
    },

    /**
     * Create an internal transfer from POS.
     * @param {Object} params - {product_id, qty, source_warehouse_id, dest_warehouse_id, user_name}
     * @returns {Object} picking data {id, name, state}
     */
    async createTransferFromPos(params) {
        try {
            this.ui.block();
            const result = await this.data.call(
                "stock.picking",
                "create_transfer_from_pos",
                [params]
            );
            this.notification.add(
                _t("Traslado %s creado. Pendiente de preparación.", result.name),
                { type: "success" }
            );
            return result;
        } catch (error) {
            const errorMsg =
                error.message || (error.data && error.data.message) || "Error desconocido";
            this.notification.add(
                _t("Error al crear el traslado: %s", errorMsg),
                { type: "danger" }
            );
            return false;
        } finally {
            this.ui.unblock();
        }
    },

    /**
     * Load transfers for this POS warehouse.
     * @param {string|false} stateFilter - 'pending', 'shipped', 'received', 'all'
     * @returns {Array} list of transfer objects
     */
    async loadTransfers(stateFilter) {
        const warehouseId = this.getTransferWarehouseId();
        if (!warehouseId) {
            this.notification.add(
                _t("No se ha podido determinar el almacén del TPV."),
                { type: "warning" }
            );
            return [];
        }
        try {
            const transfers = await this.data.call(
                "stock.picking",
                "get_transfers_for_pos",
                [warehouseId, stateFilter || false]
            );
            this._transferCache = transfers || [];
            return this._transferCache;
        } catch (error) {
            this.notification.add(
                _t("Error al cargar traslados."),
                { type: "danger" }
            );
            return [];
        }
    },

    /**
     * Receive (validate) a transfer from POS.
     * @param {number} pickingId - stock.picking id
     * @returns {Object|false} result with success flag
     */
    async receiveTransferFromPos(pickingId) {
        try {
            this.ui.block();
            const result = await this.data.call(
                "stock.picking",
                "receive_transfer_from_pos",
                [pickingId]
            );
            if (result.success) {
                this.notification.add(
                    result.message || _t("Traslado recibido correctamente."),
                    { type: "success" }
                );
            }
            return result;
        } catch (error) {
            const errorMsg =
                error.message || (error.data && error.data.message) || "Error desconocido";
            this.notification.add(
                _t("Error al recepcionar: %s", errorMsg),
                { type: "danger" }
            );
            return false;
        } finally {
            this.ui.unblock();
        }
    },
});
