import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";

patch(Orderline.prototype, {
    async onClickLocation() {
        const pos = this.env.services.pos;
        if (!pos || !this.line) {
            return;
        }
        const currentLoc = this.line.location_id;
        this.line.update({ location_id: null });
        await pos.promptLineLocation(this.line);
        if (!this.line.location_id && currentLoc) {
            this.line.update({ location_id: currentLoc });
        }
    },
});
