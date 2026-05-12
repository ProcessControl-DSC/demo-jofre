/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(TicketScreen.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    isReinvoiceVisible(order) {
        if (!order) {
            return false;
        }
        if (!this.pos.config.allow_reinvoice) {
            return false;
        }
        if (order.state !== "paid" && order.state !== "done") {
            return false;
        }
        if (order.re_invoiced) {
            return false;
        }
        if (!order.account_move) {
            return false;
        }
        return true;
    },

    async onClickReinvoice(order) {
        if (!order) {
            return;
        }
        this.dialog.add(PartnerList, {
            partner: null,
            getPayload: async (newPartner) => {
                if (!newPartner) {
                    return;
                }
                if (newPartner.id === order.partner_id?.id) {
                    this.notification.add(
                        _t("El nuevo cliente debe ser distinto del actual."),
                        { type: "warning" }
                    );
                    return;
                }
                try {
                    await this.pos.data.call(
                        "pos.order",
                        "action_pos_reinvoice",
                        [order.id],
                        { partner_id: newPartner.id }
                    );
                    await this.pos.data.read("pos.order", [order.id]);
                    this.notification.add(
                        _t("Pedido refacturado correctamente."),
                        { type: "success" }
                    );
                } catch (error) {
                    this.notification.add(
                        _t("La refacturación falló: %s",
                           error.data?.message || error.message || ""),
                        { type: "danger" }
                    );
                }
            },
        });
    },
});
