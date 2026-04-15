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
        const line = order?.lines?.length ? order.lines[order.lines.length - 1] : null;

        const popupProps = { close: () => {} };

        if (line && line.product_id) {
            const product = line.product_id;
            popupProps.productId = product.id;
            const tmpl = product.product_tmpl_id
                ? this.pos.models["product.template"]?.get(product.product_tmpl_id)
                : null;
            if (tmpl) {
                popupProps.productTemplate = tmpl;
            }
        }

        this.dialogService.add(TransferRequestPopup, popupProps);
    },
});
