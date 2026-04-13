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
            if (this.state.activeFilter === "draft") {
                states = ["draft"];
            } else if (this.state.activeFilter === "confirmed") {
                states = ["confirmed"];
            } else if (this.state.activeFilter === "under_repair") {
                states = ["under_repair"];
            } else if (this.state.activeFilter === "done") {
                states = ["done"];
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
            draft: "bg-info",
            confirmed: "bg-primary",
            under_repair: "bg-warning text-dark",
            done: "bg-success",
            cancel: "bg-danger",
        };
        return classes[state] || "bg-secondary";
    }

    getStateLabel(state) {
        const labels = {
            draft: _t("Borrador"),
            confirmed: _t("Confirmada"),
            under_repair: _t("En Curso"),
            done: _t("Finalizada"),
            cancel: _t("Cancelada"),
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

    canConfirm(alteration) {
        return alteration.state === "draft";
    }

    canStart(alteration) {
        return alteration.state === "confirmed";
    }

    canEnd(alteration) {
        return alteration.state === "under_repair";
    }

    canCancel(alteration) {
        return ["draft", "confirmed", "under_repair"].includes(alteration.state);
    }

    async onActionConfirm(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "confirm");
            this.pos.notification.add(_t("Reparación %s confirmada", alteration.name), 3000);
            await this.loadAlterations();
        } catch (e) {
            console.error("Error confirming repair:", e);
        }
    }

    async onActionStart(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "start");
            this.pos.notification.add(_t("Reparación %s iniciada", alteration.name), 3000);
            await this.loadAlterations();
        } catch (e) {
            console.error("Error starting repair:", e);
        }
    }

    async onActionEnd(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "end");
            this.pos.notification.add(
                _t("Reparación %s finalizada", alteration.name),
                3000
            );
            await this.loadAlterations();
        } catch (e) {
            console.error("Error ending repair:", e);
        }
    }

    async onActionCancel(alteration) {
        try {
            await this.pos.changeAlterationState(alteration.id, "cancel");
            this.pos.notification.add(_t("Reparación %s cancelada", alteration.name), 3000);
            await this.loadAlterations();
        } catch (e) {
            console.error("Error cancelling repair:", e);
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
