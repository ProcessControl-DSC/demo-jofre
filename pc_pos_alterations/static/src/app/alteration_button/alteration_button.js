/** @odoo-module */
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { AlterationPopup } from "@pc_pos_alterations/app/alteration_popup/alteration_popup";
import { _t } from "@web/core/l10n/translation";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },

    async onClickAlteration() {
        const order = this.pos.getOrder();
        const selectedLine = order ? order.getSelectedOrderline() : null;

        if (!selectedLine) {
            this.notification.add(_t("Seleccione una línea de pedido primero"), {
                type: "warning",
            });
            return;
        }

        this.dialog.add(AlterationPopup, {
            orderline: selectedLine,
            order: order,
        });
    },
});
