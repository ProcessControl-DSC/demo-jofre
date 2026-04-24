from odoo import api, models


class StockLocation(models.Model):
    _name = "stock.location"
    _inherit = ["stock.location", "pos.load.mixin"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        picking_type = config.picking_type_id
        source = picking_type.default_location_src_id
        if not source:
            return [("id", "=", 0)]
        return [
            ("usage", "=", "internal"),
            ("id", "child_of", source.id),
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
