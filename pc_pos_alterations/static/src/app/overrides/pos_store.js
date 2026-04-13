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
     * Obtiene los arreglos de la tienda actual.
     * @param {Array|null} states - Estados a filtrar
     * @returns {Array} Lista de arreglos
     */
    async getAlterations(states) {
        const warehouseId = this.getWarehouseId();
        if (!warehouseId) {
            return [];
        }
        const result = await this.data.call(
            "pos.alteration",
            "get_alterations_for_pos",
            [warehouseId, states || false]
        );
        this.alterations = result;
        return result;
    },

    /**
     * Cambia el estado de un arreglo.
     * @param {number} alterationId - ID del arreglo
     * @param {string} newState - Nuevo estado
     * @returns {Object} Resultado
     */
    async changeAlterationState(alterationId, newState) {
        const result = await this.data.call(
            "pos.alteration",
            "change_state_from_pos",
            [alterationId, newState]
        );
        return result;
    },

    /**
     * Busca arreglos por texto.
     * @param {string} searchTerm - Término de búsqueda
     * @returns {Array} Arreglos encontrados
     */
    async searchAlterations(searchTerm) {
        const warehouseId = this.getWarehouseId();
        if (!warehouseId) {
            return [];
        }
        const result = await this.data.call(
            "pos.alteration",
            "search_alterations_from_pos",
            [warehouseId, searchTerm]
        );
        return result;
    },
});
