/** @odoo-module */
import { Component, useState, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlterationReceipt } from "@pc_pos_alterations/app/alteration_receipt/alteration_receipt";

export class AlterationScreen extends Component {
    static template = "pc_pos_alterations.AlterationScreen";
    static props = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.printer = useService("printer");
        this.state = useState({
            alterations: [],
            activeFilter: "all",
            searchTerm: "",
            loading: false,
        });

        onWillStart(async () => {
            await this.loadAlterations();
        });
    }

    async loadAlterations() {
        this.state.loading = true;
        try {
            let states = null;
            if (this.state.activeFilter === "pending") {
                states = ["pending"];
            } else if (this.state.activeFilter === "in_progress") {
                states = ["in_progress"];
            } else if (this.state.activeFilter === "ready") {
                states = ["ready"];
            }
            if (this.state.searchTerm) {
                this.state.alterations = await this.pos.searchAlterations(
                    this.state.searchTerm
                );
            } else {
                this.state.alterations = await this.pos.getAlterations(states);
            }
        } catch (e) {
            console.error("Error loading alterations:", e);
            this.state.alterations = [];
        }
        this.state.loading = false;
    }

    async onFilterChange(filter) {
        this.state.activeFilter = filter;
        this.state.searchTerm = "";
        await this.loadAlterations();
    }

    async onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        if (this.state.searchTerm.length >= 2) {
            await this.loadAlterations();
        } else if (this.state.searchTerm.length === 0) {
            await this.loadAlterations();
        }
    }

    async onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            await this.loadAlterations();
        }
    }

    getStateBadgeClass(state) {
        const classes = {
            pending: "bg-info",
            in_progress: "bg-warning text-dark",
            ready: "bg-success",
            delivered: "bg-secondary",
            cancelled: "bg-danger",
        };
        return classes[state] || "bg-secondary";
    }

    getStateLabel(state) {
        const labels = {
            pending: _t("Pendiente"),
            in_progress: _t("En Curso"),
            ready: _t("Listo"),
            delivered: _t("Entregado"),
            cancelled: _t("Cancelado"),
        };
        return labels[state] || state;
    }

    getDeliveryMethodLabel(method) {
        if (method === "pickup_store") {
            return _t("Tienda");
        }
        if (method === "ship_customer") {
            return _t("Envío");
        }
        return "";
    }

    canStart(alteration) {
        return alteration.state === "pending";
    }

    canReady(alteration) {
        return alteration.state === "in_progress";
    }

    canDeliver(alteration) {
        return alteration.state === "ready";
    }

    canCancel(alteration) {
        return ["pending", "in_progress", "ready"].includes(alteration.state);
    }

    async onActionStart(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "in_progress");
            this.pos.notification.add(_t("Arreglo %s iniciado", alteration.name), 3000);
            await this.loadAlterations();
        } catch (e) {
            console.error("Error starting alteration:", e);
        }
    }

    async onActionReady(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "ready");
            this.pos.notification.add(
                _t("Arreglo %s listo para recoger", alteration.name),
                3000
            );
            await this.loadAlterations();
        } catch (e) {
            console.error("Error marking ready:", e);
        }
    }

    async onActionDeliver(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "delivered");
            this.pos.notification.add(
                _t("Arreglo %s entregado al cliente", alteration.name),
                3000
            );
            await this.loadAlterations();
        } catch (e) {
            console.error("Error delivering:", e);
        }
    }

    async onActionCancel(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "cancelled");
            this.pos.notification.add(_t("Arreglo %s cancelado", alteration.name), 3000);
            await this.loadAlterations();
        } catch (e) {
            console.error("Error cancelling:", e);
        }
    }

    async onPrintReceipt(alteration) {
        try {
            await this.printer.print(
                AlterationReceipt,
                { alteration },
                { webPrintFallback: true }
            );
        } catch (e) {
            console.warn("Could not print receipt:", e);
        }
    }

    onClickBack() {
        this.pos.showScreen("ProductScreen");
    }
}
