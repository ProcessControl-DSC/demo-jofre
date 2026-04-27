from odoo import api, models


class StockLocation(models.Model):
    _name = "stock.location"
    _inherit = ["stock.location", "pos.load.mixin"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        picking_type = config.picking_type_id
        parents = []
        source = picking_type.default_location_src_id
        if source:
            parents.append(source.id)
        return_pt = picking_type.return_picking_type_id or picking_type
        return_dest = return_pt.default_location_dest_id
        if return_dest and return_dest.id not in parents:
            parents.append(return_dest.id)
        if not parents:
            return [("id", "=", 0)]
        return [
            ("usage", "=", "internal"),
            ("id", "child_of", parents),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "name",
            "complete_name",
            "parent_path",
            "location_id",
            "usage",
        ]
