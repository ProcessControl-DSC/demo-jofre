/** @odoo-module **/

import { ProductMatrixDialog } from "@product_matrix/js/product_matrix_dialog";
import { StoreDistribution } from "@pc_fashion_matrix/js/store_distribution";
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class FashionMatrixDialog extends ProductMatrixDialog {
    static template = "pc_fashion_matrix.FashionMatrixDialog";
    static components = { ...ProductMatrixDialog.components, StoreDistribution };
    static props = {
        ...ProductMatrixDialog.props,
        cost_price: { type: Number, optional: true },
        sale_price: { type: Number, optional: true },
        stores: { type: Array, optional: true },
        is_fashion_mode: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.state = useState({
            rowTotals: [],
            colTotals: [],
            grandTotal: 0,
            totalAmount: 0,
            storeDistribution: [],
        });
        this.matrixRef = useRef('productMatrix');

        onMounted(() => {
            this._attachInputListeners();
            this._computeTotals();
        });
    }

    _attachInputListeners() {
        const table = this.matrixRef.el;
        if (!table) return;
        table.addEventListener('input', (ev) => {
            if (ev.target.classList.contains('o_matrix_input')) {
                this._computeTotals();
            }
        });
    }

    _computeTotals() {
        const inputs = document.getElementsByClassName('o_matrix_input');
        if (!inputs.length) return;

        const rows = this.props.rows;
        const numCols = this.props.header.length - 1;
        const numRows = rows.length;

        const rowTotals = new Array(numRows).fill(0);
        const colTotals = new Array(numCols).fill(0);

        let idx = 0;
        for (let r = 0; r < numRows; r++) {
            const row = rows[r];
            for (let c = 0; c < row.length; c++) {
                const cell = row[c];
                if (cell && cell.ptav_ids !== undefined) {
                    const input = inputs[idx];
                    if (input) {
                        const val = parseFloat(input.value) || 0;
                        rowTotals[r] += val;
                        colTotals[c - 1] += val; // -1 porque primera celda es header fila
                    }
                    idx++;
                }
            }
        }

        const grandTotal = rowTotals.reduce((s, v) => s + v, 0);
        const costPrice = this.props.cost_price || 0;

        this.state.rowTotals = rowTotals;
        this.state.colTotals = colTotals;
        this.state.grandTotal = grandTotal;
        this.state.totalAmount = grandTotal * costPrice;

        // Auto-distribuir por tiendas si hay stores
        if (this.props.stores && this.props.stores.length > 0) {
            this._computeStoreDistribution(grandTotal);
        }
    }

    _computeStoreDistribution(totalQty) {
        const stores = this.props.stores || [];
        if (!stores.length || totalQty <= 0) {
            this.state.storeDistribution = [];
            return;
        }
        this.state.storeDistribution = this._distributeHund(totalQty, stores);
    }

    /**
     * Método de Hund (largest remainder method) para distribución proporcional.
     */
    _distributeHund(totalQty, stores) {
        const allocations = stores.map(s => {
            const raw = totalQty * s.percentage / 100;
            return {
                warehouse_id: s.warehouse_id,
                warehouse_name: s.warehouse_name,
                percentage: s.percentage,
                raw: raw,
                qty: Math.floor(raw),
                remainder: raw - Math.floor(raw),
            };
        });

        let distributed = allocations.reduce((s, a) => s + a.qty, 0);
        let leftover = totalQty - distributed;

        // Asignar unidades restantes por mayor fracción decimal
        allocations.sort((a, b) => b.remainder - a.remainder);
        for (let i = 0; i < leftover; i++) {
            allocations[i].qty += 1;
        }

        return allocations.filter(a => a.qty > 0);
    }

    _onConfirm() {
        // Recoger datos del grid estándar
        const inputs = document.getElementsByClassName('o_matrix_input');
        const matrixChanges = [];
        for (const matrixInput of inputs) {
            if (matrixInput.value && matrixInput.value !== matrixInput.attributes.value.nodeValue) {
                matrixChanges.push({
                    qty: parseFloat(matrixInput.value),
                    ptav_ids: matrixInput.attributes.ptav_ids.nodeValue.split(",").map(
                        id => parseInt(id)
                    ),
                });
            }
        }

        // Añadir distribución por tienda al grid JSON
        const gridData = {
            product_template_id: this.props.product_template_id,
            changes: matrixChanges,
        };

        if (this.state.storeDistribution.length > 0) {
            gridData.store_distribution = this.state.storeDistribution.map(s => ({
                warehouse_id: s.warehouse_id,
                warehouse_name: s.warehouse_name,
                qty: s.qty,
            }));
        }

        this.props.record.update({
            grid: JSON.stringify(gridData),
            grid_update: true,
        });
        this.props.close();
    }
}
