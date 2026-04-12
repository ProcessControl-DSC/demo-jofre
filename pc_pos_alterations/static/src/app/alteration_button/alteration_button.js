/** @odoo-module */
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { AlterationPopup } from "@pc_pos_alterations/app/alteration_popup/alteration_popup";
import { AlterationReceipt } from "@pc_pos_alterations/app/alteration_receipt/alteration_receipt";
import { _t } from "@web/core/l10n/translation";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.printer = useService("printer");
    },

    async onClickAlteration() {
        const order = this.pos.getOrder();
        const selectedLine = order ? order.getSelectedOrderline() : null;

        if (!selectedLine) {
            this.pos.notification.add(_t("Seleccione una línea de pedido primero"), 3000);
            return;
        }

        this.dialog.add(AlterationPopup, {
            orderline: selectedLine,
            order: order,
            getPayload: async (alterationData) => {
                if (alterationData) {
                    this.pos.notification.add(
                        _t("Arreglo %s creado correctamente", alterationData.name),
                        3000
                    );
                    // Render and print the alteration receipt
                    try {
                        await this.printer.print(AlterationReceipt, {
                            alteration: alterationData,
                        }, { webPrintFallback: true });
                    } catch (e) {
                        console.warn("Could not print alteration receipt:", e);
                    }
                }
            },
        });
    },
});
