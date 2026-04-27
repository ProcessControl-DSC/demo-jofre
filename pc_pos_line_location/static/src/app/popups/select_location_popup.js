import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class SelectLocationPopup extends Component {
    static template = "pc_pos_line_location.SelectLocationPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        productName: { type: String, optional: true },
        totalQty: { type: Number },
        candidates: Array,
        initialAllocations: { type: Object, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Select source location"),
        productName: "",
        initialAllocations: null,
    };

    setup() {
        const allocations = {};
        for (const c of this.props.candidates) {
            allocations[c.location.id] = 0;
        }
        if (this.props.initialAllocations) {
            for (const [locId, qty] of Object.entries(this.props.initialAllocations)) {
                if (locId in allocations) {
                    allocations[locId] = qty;
                }
            }
        } else if (this.props.candidates.length > 0) {
            allocations[this.props.candidates[0].location.id] = this.props.totalQty;
        }
        this.state = useState({ allocations });
    }

    onInput(locId, ev) {
        const raw = parseFloat(ev.target.value);
        const val = isNaN(raw) || raw < 0 ? 0 : raw;
        this.state.allocations[locId] = val;
    }

    fillFromCandidate(c) {
        this.state.allocations[c.location.id] = c.available;
    }

    get assignedTotal() {
        return Object.values(this.state.allocations).reduce(
            (a, b) => a + (parseFloat(b) || 0),
            0
        );
    }

    get isValid() {
        return Math.abs(this.assignedTotal - this.props.totalQty) < 0.0001;
    }

    get totalDelta() {
        return this.assignedTotal - this.props.totalQty;
    }

    confirm() {
        if (!this.isValid) {
            return;
        }
        const payload = [];
        for (const c of this.props.candidates) {
            const qty = parseFloat(this.state.allocations[c.location.id]) || 0;
            if (qty > 0) {
                payload.push({ location: c.location, qty });
            }
        }
        this.props.getPayload(payload);
        this.props.close();
    }

    cancel() {
        this.props.getPayload(null);
        this.props.close();
    }
}
