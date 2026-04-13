/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.alterations = [];
    },

    async processServerData() {
        await super.processServerData(...arguments);
        // alteration.type data is loaded automatically via pos.load.mixin
    },

    /**
     * Obtiene el warehouse_id de la configuración actual del TPV.
     * @returns {number|false}
     */
    getWarehouseId() {
        const pickingType = this.config.picking_type_id;
        if (pickingType && pickingType.warehouse_id) {
            return pickingType.warehouse_id.id;
        }
        return false;
    },

    /**
     * Obtiene los arreglos (repair.order) de la tienda actual.
     * @param {Array|null} states - Estados a filtrar
     * @returns {Array} Lista de reparaciones
     */
    async getAlterations(states) {
        const warehouseId = this.getWarehouseId();
        if (!warehouseId) {
            return [];
        }
        const result = await this.data.call(
            "repair.order",
            "get_repairs_for_pos",
            [warehouseId, states || false]
        );
        this.alterations = result;
        return result;
    },

    /**
     * Cambia el estado de una reparación.
     * @param {number} repairId - ID de la reparación
     * @param {string} action - Acción: 'confirm', 'start', 'end', 'cancel'
     * @returns {Object} Resultado
     */
    async changeAlterationState(repairId, action) {
        const result = await this.data.call(
            "repair.order",
            "change_repair_state_from_pos",
            [repairId, action]
        );
        return result;
    },

    /**
     * Busca reparaciones por texto.
     * @param {string} searchTerm - Término de búsqueda
     * @returns {Array} Reparaciones encontradas
     */
    async searchAlterations(searchTerm) {
        const warehouseId = this.getWarehouseId();
        if (!warehouseId) {
            return [];
        }
        const result = await this.data.call(
            "repair.order",
            "search_repairs_from_pos",
            [warehouseId, searchTerm]
        );
        return result;
    },
});
