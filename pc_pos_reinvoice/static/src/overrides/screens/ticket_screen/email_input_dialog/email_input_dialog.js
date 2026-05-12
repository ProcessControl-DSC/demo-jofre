/** @odoo-module */

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class EmailInputDialog extends Component {
    static template = "pc_pos_reinvoice.EmailInputDialog";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        body: { type: String, optional: true },
        confirmLabel: { type: String, optional: true },
        cancelLabel: { type: String, optional: true },
        startingValue: { type: String, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Enviar por correo electrónico"),
        body: "",
        confirmLabel: _t("Enviar"),
        cancelLabel: _t("Cancelar"),
        startingValue: "",
    };

    setup() {
        this.state = useState({
            email: this.props.startingValue || "",
            error: "",
        });
        this.inputRef = useRef("emailInput");
        onMounted(() => this.inputRef.el?.focus());
    }

    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    confirm() {
        const email = (this.state.email || "").trim();
        if (!this.isValidEmail(email)) {
            this.state.error = _t("Introduce un correo electrónico válido.");
            return;
        }
        this.props.getPayload(email);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }

    onKeyup(ev) {
        if (ev.key === "Enter") {
            this.confirm();
        }
    }
}
