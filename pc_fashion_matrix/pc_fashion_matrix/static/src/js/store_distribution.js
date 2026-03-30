/** @odoo-module **/

import { Component } from "@odoo/owl";

export class StoreDistribution extends Component {
    static template = "pc_fashion_matrix.StoreDistribution";
    static props = {
        distribution: { type: Array },
        grandTotal: { type: Number },
        costPrice: { type: Number },
    };
}
