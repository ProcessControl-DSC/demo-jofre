/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this._reservationCache = [];
    },

    // =========================================================================
    // RESERVATION: CREATE
    // =========================================================================

    /**
     * Create a reservation from the current POS order lines.
     * Validates that a partner is selected and there are order lines.
     * @returns {Object|false} reservation data or false
     */
    async createReservation() {
        const order = this.getOrder();
        if (!order) {
            this.notification.add(_t("No hay pedido activo."), { type: "warning" });
            return false;
        }

        const partner = order.getPartner();
        if (!partner) {
            this.notification.add(
                _t("Debe seleccionar un cliente antes de reservar."),
                { type: "warning" }
            );
            return false;
        }

        const lines = order.getOrderlines();
        if (!lines || lines.length === 0) {
            this.notification.add(
                _t("Debe añadir al menos un producto al pedido."),
                { type: "warning" }
            );
            return false;
        }

        // Build the lines data
        const reservationLines = lines.map((line) => ({
            product_id: line.product_id.id,
            product_qty: line.getQuantity(),
            price_unit: line.getUnitPrice(),
        }));

        // Build items summary for confirmation
        const itemsSummary = lines
            .map((line) => `  - ${line.getQuantity()}x ${line.getFullProductName()}`)
            .join("\n");

        // Ask for confirmation
        const confirmed = await ask(this.dialog, {
            title: _t("Confirmar reserva"),
            body: _t(
                "¿Reservar %s artículo(s) para %s?\n\n%s\n\nLa reserva expirará en 7 días.",
                String(lines.length),
                partner.name,
                itemsSummary
            ),
        });

        if (!confirmed) {
            return false;
        }

        try {
            this.ui.block();
            const result = await this.data.call(
                "product.reservation",
                "create_from_pos",
                [
                    {
                        partner_id: partner.id,
                        config_id: this.config.id,
                        note: "",
                        lines: reservationLines,
                    },
                ]
            );

            this.notification.add(
                _t("Reserva %s creada correctamente para %s.", result.name, partner.name),
                { type: "success" }
            );

            // Clear the current order
            this.removeOrder(order);
            this.addNewOrder();

            return result;
        } catch (error) {
            const errorMsg =
                error.message || (error.data && error.data.message) || "Error desconocido";
            this.notification.add(_t("Error al crear la reserva: %s", errorMsg), {
                type: "danger",
            });
            return false;
        } finally {
            this.ui.unblock();
        }
    },

    // =========================================================================
    // RESERVATION: LOAD LIST
    // =========================================================================

    /**
     * Fetch active reservations for this POS config's warehouse.
     * @returns {Array} list of reservation objects
     */
    async loadReservations() {
        try {
            const reservations = await this.data.call(
                "product.reservation",
                "get_reservations_for_pos",
                [this.config.id]
            );
            this._reservationCache = reservations || [];
            return this._reservationCache;
        } catch (error) {
            this.notification.add(
                _t("Error al cargar reservas."),
                { type: "danger" }
            );
            return [];
        }
    },

    // =========================================================================
    // RESERVATION: CANCEL
    // =========================================================================

    /**
     * Cancel a reservation from POS.
     * @param {number} reservationId
     * @returns {boolean} success
     */
    async cancelReservation(reservationId) {
        const confirmed = await ask(this.dialog, {
            title: _t("Cancelar reserva"),
            body: _t(
                "¿Está seguro de que desea cancelar esta reserva? El stock volverá al almacén."
            ),
        });

        if (!confirmed) {
            return false;
        }

        try {
            this.ui.block();
            const result = await this.data.call(
                "product.reservation",
                "cancel_from_pos",
                [reservationId]
            );

            if (result.success) {
                this.notification.add(_t("Reserva cancelada correctamente."), {
                    type: "success",
                });
            } else {
                this.notification.add(result.message, { type: "danger" });
            }
            return result.success;
        } catch (error) {
            this.notification.add(_t("Error al cancelar la reserva."), { type: "danger" });
            return false;
        } finally {
            this.ui.unblock();
        }
    },

    // =========================================================================
    // RESERVATION: CHARGE (COBRAR)
    // =========================================================================

    /**
     * Load reservation items into the current POS order for payment.
     * @param {Object} reservation - The reservation data object
     * @returns {boolean} success
     */
    async chargeReservation(reservation) {
        try {
            // Create a new order
            const order = this.addNewOrder();

            // Set the partner
            const partner = this.models["res.partner"].get(reservation.partner_id);
            if (partner) {
                order.setPartner(partner);
            }

            // Add lines from the reservation
            for (const line of reservation.lines) {
                const product = this.models["product.product"].get(line.product_id);
                if (product) {
                    await this.addLineToCurrentOrder({
                        product_id: product,
                        qty: line.product_qty,
                        price_unit: line.price_unit,
                    });
                }
            }

            // Store reservation reference in the order for later marking as done
            order.pc_reservation_id = reservation.id;
            order.pc_reservation_name = reservation.name;

            this.notification.add(
                _t("Artículos de la reserva %s cargados en el pedido.", reservation.name),
                { type: "info" }
            );

            return true;
        } catch (error) {
            this.notification.add(
                _t("Error al cargar la reserva en el pedido."),
                { type: "danger" }
            );
            return false;
        }
    },

    // =========================================================================
    // RESERVATION: MARK DONE AFTER PAYMENT
    // =========================================================================

    /**
     * Mark a reservation as done after POS payment completes.
     * Called from the payment flow when the order is paid.
     * @param {Object} order - The POS order
     */
    async markReservationDoneIfNeeded(order) {
        if (!order.pc_reservation_id) {
            return;
        }
        try {
            await this.data.call(
                "product.reservation",
                "mark_done_from_pos",
                [order.pc_reservation_id, order.id || false]
            );
        } catch (error) {
            // Log but don't block the payment flow
            this.notification.add(
                _t("Aviso: no se pudo marcar la reserva como cobrada."),
                { type: "warning" }
            );
        }
    },
});
