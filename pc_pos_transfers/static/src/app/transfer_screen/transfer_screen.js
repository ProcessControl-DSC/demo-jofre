/** @odoo-module */
import { Component, useState, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";

const { DateTime } = luxon;

/**
 * TransferScreen - Full-screen dialog to manage stock transfers from POS.
 *
 * Shows incoming transfers to the current warehouse with filter tabs for
 * status (Pendientes, En camino, Recibidos, Todos) and allows receiving
 * transfers that are in 'assigned' state.
 */
export class TransferScreen extends Component {
    static template = "pc_pos_transfers.TransferScreen";
    static components = { Dialog };
    static props = {
        close: { type: Function, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            transfers: [],
            filteredTransfers: [],
            activeFilter: "all",
            searchText: "",
            isLoading: true,
            selectedTransferId: null,
        });

        onWillStart(async () => {
            await this.loadTransfers();
        });
    }

    // =========================================================================
    // DATA LOADING
    // =========================================================================

    async loadTransfers() {
        this.state.isLoading = true;
        try {
            let stateFilter = false;
            if (this.state.activeFilter !== "all") {
                stateFilter = this.state.activeFilter;
            }
            this.state.transfers = await this.pos.loadTransfers(stateFilter);
            this.applySearch();
        } catch (error) {
            console.error("Error loading transfers:", error);
            this.state.transfers = [];
            this.state.filteredTransfers = [];
        } finally {
            this.state.isLoading = false;
        }
    }

    applySearch() {
        const search = this.state.searchText.toLowerCase().trim();
        if (!search) {
            this.state.filteredTransfers = [...this.state.transfers];
        } else {
            this.state.filteredTransfers = this.state.transfers.filter((t) => {
                const nameMatch = (t.name || "").toLowerCase().includes(search);
                const originMatch = (t.origin || "").toLowerCase().includes(search);
                const whMatch = (t.source_warehouse || "").toLowerCase().includes(search);
                const productMatch = (t.products || []).some((p) =>
                    (p.product_name || "").toLowerCase().includes(search)
                );
                return nameMatch || originMatch || whMatch || productMatch;
            });
        }
    }

    // =========================================================================
    // FILTER AND SEARCH EVENTS
    // =========================================================================

    async onFilterChange(filter) {
        this.state.activeFilter = filter;
        this.state.searchText = "";
        this.state.selectedTransferId = null;
        await this.loadTransfers();
    }

    onSearchInput(ev) {
        this.state.searchText = ev.target.value;
        this.applySearch();
    }

    // =========================================================================
    // SELECTION
    // =========================================================================

    selectTransfer(transferId) {
        this.state.selectedTransferId =
            this.state.selectedTransferId === transferId ? null : transferId;
    }

    get selectedTransfer() {
        if (!this.state.selectedTransferId) {
            return null;
        }
        return this.state.filteredTransfers.find(
            (t) => t.id === this.state.selectedTransferId
        );
    }

    // =========================================================================
    // STATE DISPLAY HELPERS
    // =========================================================================

    getStateBadgeClass(posState) {
        const classes = {
            pending: "text-bg-warning",
            shipped: "text-bg-primary",
            received: "text-bg-success",
            cancelled: "text-bg-secondary",
        };
        return classes[posState] || "text-bg-secondary";
    }

    getStateLabel(posState) {
        const labels = {
            pending: _t("Pendiente"),
            shipped: _t("Enviado"),
            received: _t("Recibido"),
            cancelled: _t("Cancelado"),
        };
        return labels[posState] || posState;
    }

    getStateIcon(posState) {
        const icons = {
            pending: "fa-clock-o",
            shipped: "fa-truck",
            received: "fa-check-circle",
            cancelled: "fa-ban",
        };
        return icons[posState] || "fa-question";
    }

    /**
     * Check if a transfer can be received from POS.
     * Only assigned (shipped) transfers can be received.
     */
    canReceive(transfer) {
        return transfer.pos_state === "shipped";
    }

    // =========================================================================
    // DATE HELPERS
    // =========================================================================

    formatDate(dateStr) {
        if (!dateStr) {
            return "";
        }
        try {
            return DateTime.fromISO(dateStr).toFormat("dd/MM/yyyy HH:mm");
        } catch {
            return dateStr;
        }
    }

    getTimeAgo(dateStr) {
        if (!dateStr) {
            return "";
        }
        try {
            const dt = DateTime.fromISO(dateStr);
            const now = DateTime.now();
            const diff = now.diff(dt, ["days", "hours", "minutes"]);

            if (diff.days >= 1) {
                const days = Math.floor(diff.days);
                return _t("hace %s d", String(days));
            }
            if (diff.hours >= 1) {
                const hours = Math.floor(diff.hours);
                return _t("hace %s h", String(hours));
            }
            const mins = Math.max(0, Math.floor(diff.minutes));
            return _t("hace %s min", String(mins));
        } catch {
            return "";
        }
    }

    // =========================================================================
    // PRODUCT SUMMARY
    // =========================================================================

    getProductSummary(transfer) {
        if (!transfer.products || transfer.products.length === 0) {
            return _t("Sin productos");
        }
        if (transfer.products.length === 1) {
            return transfer.products[0].product_name;
        }
        return _t(
            "%s y %s más",
            transfer.products[0].product_name,
            String(transfer.products.length - 1)
        );
    }

    getTotalQtyDemanded(transfer) {
        if (!transfer.products) {
            return 0;
        }
        return transfer.products.reduce((acc, p) => acc + (p.qty_demanded || 0), 0);
    }

    // =========================================================================
    // ACTIONS
    // =========================================================================

    async onClickReceive() {
        const transfer = this.selectedTransfer;
        if (!transfer || !this.canReceive(transfer)) {
            return;
        }

        const confirmed = await ask(this.dialog, {
            title: _t("Confirmar recepción"),
            body: _t(
                "¿Confirmar la recepción del traslado %s?\n\n" +
                "Esto validará la entrada de los productos en tu almacén.",
                transfer.name
            ),
        });

        if (!confirmed) {
            return;
        }

        const result = await this.pos.receiveTransferFromPos(transfer.id);
        if (result && result.success) {
            this.state.selectedTransferId = null;
            await this.loadTransfers();
        }
    }

    async onClickRefresh() {
        this.state.selectedTransferId = null;
        await this.loadTransfers();
    }

    onClickClose() {
        if (this.props.close) {
            this.props.close();
        }
    }

    // =========================================================================
    // COUNTERS FOR FILTER BADGES
    // =========================================================================

    getFilterCount(filter) {
        if (filter === "all") {
            return this.state.transfers.length;
        }
        return this.state.transfers.filter((t) => t.pos_state === filter).length;
    }
}
