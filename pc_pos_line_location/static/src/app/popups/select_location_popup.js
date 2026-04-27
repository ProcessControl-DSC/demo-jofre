import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class SelectLocationPopup extends Component {
    static template = "pc_pos_line_location.SelectLocationPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        productName: { type: String, optional: true },
        candidates: Array,
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Select source location"),
        productName: "",
    };

    select(candidate) {
        this.props.getPayload(candidate.location);
        this.props.close();
    }

    cancel() {
        this.props.getPayload(null);
        this.props.close();
    }
}
