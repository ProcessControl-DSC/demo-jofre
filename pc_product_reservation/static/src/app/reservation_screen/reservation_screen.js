/** @odoo-module */
import { Component, useState, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

const { DateTime } = luxon;

/**
 * ReservationListPopup - Full-screen dialog for managing reservations from POS.
 * Lists confirmed reservations for the current store/warehouse and allows
 * the cashier to charge (load into order) or cancel them.
 */
export class ReservationListPopup extends Component {
    static template = "pc_product_reservation.ReservationListPopup";
    static components = { Dialog };
    static props = {
        close: { type: Function, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");
        this.state = useState({
            reservations: [],
            filteredReservations: [],
            searchText: "",
            isLoading: true,
            selectedReservationId: null,
        });

        onWillStart(async () => {
            await this.loadReservations();
        });
    }

    async loadReservations() {
        this.state.isLoading = true;
        try {
            this.state.reservations = await this.pos.loadReservations();
            this.applyFilter();
        } catch (error) {
            this.state.reservations = [];
            this.state.filteredReservations = [];
        } finally {
            this.state.isLoading = false;
        }
    }

    applyFilter() {
        const search = this.state.searchText.toLowerCase().trim();
        if (!search) {
            this.state.filteredReservations = [...this.state.reservations];
        } else {
            this.state.filteredReservations = this.state.reservations.filter((r) => {
                const partnerMatch = (r.partner_name || "").toLowerCase().includes(search);
                const nameMatch = (r.name || "").toLowerCase().includes(search);
                const productMatch = (r.lines || []).some((l) =>
                    (l.product_name || "").toLowerCase().includes(search)
                );
                return partnerMatch || nameMatch || productMatch;
            });
        }
    }

    onSearchInput(ev) {
        this.state.searchText = ev.target.value;
        this.applyFilter();
    }

    selectReservation(reservationId) {
        this.state.selectedReservationId =
            this.state.selectedReservationId === reservationId ? null : reservationId;
    }

    get selectedReservation() {
        if (!this.state.selectedReservationId) {
            return null;
        }
        return this.state.filteredReservations.find(
            (r) => r.id === this.state.selectedReservationId
        );
    }

    formatDate(dateStr) {
        if (!dateStr) {
            return "";
        }
        try {
            return DateTime.fromISO(dateStr.replace(" ", "T")).toFormat("dd/MM/yyyy HH:mm");
        } catch {
            return dateStr;
        }
    }

    getExpiryCountdown(dateStr) {
        if (!dateStr) {
            return "";
        }
        try {
            const expiry = DateTime.fromISO(dateStr.replace(" ", "T"));
            const now = DateTime.now();
            const diff = expiry.diff(now, ["days", "hours", "minutes"]);
            if (diff.days < 0 || (diff.days === 0 && diff.hours < 0)) {
                return _t("Expirada");
            }
            if (diff.days > 0) {
                return _t(
                    "%s d %s h",
                    String(Math.floor(diff.days)),
                    String(Math.floor(diff.hours))
                );
            }
            if (diff.hours > 0) {
                return _t(
                    "%s h %s min",
                    String(Math.floor(diff.hours)),
                    String(Math.floor(diff.minutes))
                );
            }
            return _t("%s min", String(Math.max(0, Math.floor(diff.minutes))));
        } catch {
            return "";
        }
    }

    isExpiringSoon(dateStr) {
        if (!dateStr) {
            return false;
        }
        try {
            const expiry = DateTime.fromISO(dateStr.replace(" ", "T"));
            const now = DateTime.now();
            const hoursLeft = expiry.diff(now, "hours").hours;
            return hoursLeft >= 0 && hoursLeft <= 48;
        } catch {
            return false;
        }
    }

    isExpired(dateStr) {
        if (!dateStr) {
            return false;
        }
        try {
            const expiry = DateTime.fromISO(dateStr.replace(" ", "T"));
            return expiry < DateTime.now();
        } catch {
            return false;
        }
    }

    getTotalAmount(reservation) {
        if (!reservation.lines) {
            return 0;
        }
        return reservation.lines.reduce((acc, l) => acc + l.product_qty * l.price_unit, 0);
    }

    formatCurrency(amount) {
        return this.pos.env.utils.formatCurrency(amount);
    }

    async onClickCharge() {
        const reservation = this.selectedReservation;
        if (!reservation) {
            return;
        }
        const success = await this.pos.chargeReservation(reservation);
        if (success && this.props.close) {
            this.props.close();
        }
    }

    async onClickCancel() {
        const reservation = this.selectedReservation;
        if (!reservation) {
            return;
        }
        const success = await this.pos.cancelReservation(reservation.id);
        if (success) {
            this.state.selectedReservationId = null;
            await this.loadReservations();
        }
    }

    async onClickRefresh() {
        this.state.selectedReservationId = null;
        await this.loadReservations();
    }

    onClickClose() {
        if (this.props.close) {
            this.props.close();
        }
    }
}
