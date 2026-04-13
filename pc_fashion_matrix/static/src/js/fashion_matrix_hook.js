/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ProductMatrixDialog } from "@product_matrix/js/product_matrix_dialog";
import { FashionMatrixDialog } from "@pc_fashion_matrix/js/fashion_matrix_dialog";

/**
 * Fashion Matrix Configurator Hook
 *
 * Replaces the standard useMatrixConfigurator hook used by purchase and sale
 * product field components. When the product has a matrix structure (Color x Size),
 * opens the enhanced FashionMatrixDialog instead of the standard ProductMatrixDialog.
 *
 * For products that do not qualify (e.g. single attribute or no matrix cells),
 * falls back to the standard ProductMatrixDialog.
 *
 * The hook is injected into PurchaseOrderLineProductField and SaleOrderLineProductField
 * via patches in fashion_purchase_field.js and fashion_sale_field.js.
 */

/**
 * Determine if a product template is a "fashion" product by checking
 * if it has both Color and Size attribute types via the matrix data.
 * This is done by inspecting the matrix header/rows structure.
 */
function looksLikeFashionMatrix(header, rows) {
    // A fashion matrix has at least 2 attributes (Color + Size)
    // and at least 2 rows of data. The standard matrix has:
    // header = [corner, col1, col2, ...]
    // rows = [[rowHeader, cell, cell, ...], ...]
    if (!header || !rows) return false;
    if (header.length < 3) return false; // corner + at least 2 size columns
    if (rows.length < 1) return false; // at least 1 color row
    // Check that rows have cells with ptav_ids (variant combinations)
    for (const row of rows) {
        for (const cell of row) {
            if (cell.ptav_ids && cell.is_possible_combination) {
                return true;
            }
        }
    }
    return false;
}

/**
 * Custom hook that replaces the standard useMatrixConfigurator.
 * Opens FashionMatrixDialog instead of ProductMatrixDialog when
 * the product has fashion attributes (detected from matrix structure).
 */
export function useFashionMatrixConfigurator() {
    const dialog = useService("dialog");

    const openDialog = (rootRecord, jsonInfo, productTemplateId, editedCellAttributes) => {
        const infos = JSON.parse(jsonInfo);

        // Determine if this is a fashion product
        const isFashion = looksLikeFashionMatrix(infos.header, infos.matrix);

        if (isFashion) {
            dialog.add(FashionMatrixDialog, {
                header: infos.header,
                rows: infos.matrix,
                editedCellAttributes: editedCellAttributes.toString(),
                product_template_id: productTemplateId,
                record: rootRecord,
            });
        } else {
            // Fallback to standard dialog
            dialog.add(ProductMatrixDialog, {
                header: infos.header,
                rows: infos.matrix,
                editedCellAttributes: editedCellAttributes.toString(),
                product_template_id: productTemplateId,
                record: rootRecord,
            });
        }
    };

    const open = async (record, edit) => {
        const rootRecord = record.model.root;

        // Fetch matrix information from server (same as standard)
        await rootRecord.update({
            grid_product_tmpl_id: record.data.product_template_id,
        });

        const updatedLineAttributes = [];
        if (edit) {
            for (const ptnvav of record.data.product_no_variant_attribute_value_ids.records) {
                updatedLineAttributes.push(ptnvav.resId);
            }
            for (const ptav of record.data.product_template_attribute_value_ids.records) {
                updatedLineAttributes.push(ptav.resId);
            }
            updatedLineAttributes.sort((a, b) => a - b);
        }

        openDialog(
            rootRecord,
            rootRecord.data.grid,
            record.data.product_template_id.id,
            updatedLineAttributes,
        );

        if (!edit) {
            rootRecord.data.order_line.delete(record);
        }
    };

    return { open };
}
