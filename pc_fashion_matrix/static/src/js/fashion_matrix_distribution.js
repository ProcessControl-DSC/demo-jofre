/** @odoo-module **/

/**
 * Largest Remainder Method (Hund / Hamilton) for distributing integer
 * quantities across stores based on percentage allocations.
 *
 * This ensures that:
 *   - Each store gets a non-negative integer quantity
 *   - The sum of all store quantities equals exactly totalQty
 *   - Rounding errors are resolved by giving extra units to stores
 *     with the largest fractional remainders
 *
 * @param {number} totalQty - Total integer quantity to distribute
 * @param {Object[]} storePercentages - Array of {warehouseId, percentage}
 * @returns {Object} Map of warehouseId -> integer quantity
 */
export function distributeHund(totalQty, storePercentages) {
    if (!storePercentages || storePercentages.length === 0 || totalQty <= 0) {
        const result = {};
        for (const sp of (storePercentages || [])) {
            result[sp.warehouseId] = 0;
        }
        return result;
    }

    // Normalize percentages to ensure they sum to 100
    const totalPct = storePercentages.reduce((sum, sp) => sum + sp.percentage, 0);
    if (totalPct <= 0) {
        const result = {};
        for (const sp of storePercentages) {
            result[sp.warehouseId] = 0;
        }
        return result;
    }

    // Calculate ideal quotas
    const quotas = storePercentages.map(sp => ({
        warehouseId: sp.warehouseId,
        quota: (totalQty * sp.percentage) / totalPct,
    }));

    // Floor each quota for initial allocation
    const result = {};
    for (const q of quotas) {
        result[q.warehouseId] = Math.floor(q.quota);
    }

    // Calculate remaining units to distribute
    const allocated = Object.values(result).reduce((sum, v) => sum + v, 0);
    let remainder = totalQty - allocated;

    // Sort by fractional remainder descending
    const sortedByRemainder = [...quotas].sort((a, b) => {
        const remA = a.quota - Math.floor(a.quota);
        const remB = b.quota - Math.floor(b.quota);
        return remB - remA;
    });

    // Distribute remaining units one by one to highest remainders
    for (let i = 0; i < remainder && i < sortedByRemainder.length; i++) {
        result[sortedByRemainder[i].warehouseId] += 1;
    }

    return result;
}

/**
 * Distribute a full matrix (colors x sizes) across stores.
 *
 * @param {Object} matrixQtys - Nested object {colorId: {sizeId: qty}}
 * @param {Object[]} storePercentages - Array of {warehouseId, percentage}
 * @returns {Object} Nested object {warehouseId: {colorId: {sizeId: qty}}}
 */
export function distributeMatrixToStores(matrixQtys, storePercentages) {
    const distribution = {};

    // Initialize structure
    for (const sp of storePercentages) {
        distribution[sp.warehouseId] = {};
    }

    // For each cell in the matrix, distribute using Hund
    for (const colorId of Object.keys(matrixQtys)) {
        for (const sp of storePercentages) {
            distribution[sp.warehouseId][colorId] = {};
        }
        for (const sizeId of Object.keys(matrixQtys[colorId])) {
            const cellQty = matrixQtys[colorId][sizeId] || 0;
            if (cellQty > 0) {
                const cellDistribution = distributeHund(cellQty, storePercentages);
                for (const sp of storePercentages) {
                    distribution[sp.warehouseId][colorId][sizeId] =
                        cellDistribution[sp.warehouseId] || 0;
                }
            } else {
                for (const sp of storePercentages) {
                    distribution[sp.warehouseId][colorId][sizeId] = 0;
                }
            }
        }
    }

    return distribution;
}
