/** @odoo-module */
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { TransferRequestPopup } from "@pc_pos_transfers/app/transfer_request/transfer_request_popup";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialogService = useService("dialog");
    },
    onClickTransferRequest() {
        const order = this.pos.getOrder();
        const selectedLine = order?.getSelectedOrderline ? order.getSelectedOrderline() : null;
        const selectedLine2 = selectedLine || (order?.lines?.length ? order.lines[order.lines.length - 1] : null);
        
        let productTemplate = null;
        let productId = false;
        if (selectedLine2 && selectedLine2.product_id) {
            const product = selectedLine2.product_id;
            productId = product.id;
            productTemplate = product.product_tmpl_id 
                ? this.pos.models["product.template"]?.get(product.product_tmpl_id) 
                : null;
        }
        
        this.dialogService.add(TransferRequestPopup, {
            productTemplate: productTemplate,
            productId: productId,
            warehouseName: '',
            availableQty: 0,
            availableWarehouses: [],
            close: () => {},
        });
    },
});
