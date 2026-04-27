from odoo import api, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    @api.model
    def _load_pos_data_domain(self, data, config):
        ids = [config.picking_type_id.id]
        return_pt = config.picking_type_id.return_picking_type_id
        if return_pt and return_pt.id not in ids:
            ids.append(return_pt.id)
        return [("id", "in", ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        for f in (
            "default_location_src_id",
            "default_location_dest_id",
            "return_picking_type_id",
        ):
            if f not in fields:
                fields.append(f)
        return fields
