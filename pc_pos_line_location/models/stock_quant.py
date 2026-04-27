from odoo import api, models


class StockQuant(models.Model):
    _name = "stock.quant"
    _inherit = ["stock.quant", "pos.load.mixin"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        picking_type = config.picking_type_id
        source = picking_type.default_location_src_id
        if not source:
            return [("id", "=", 0)]
        return [
            ("location_id.usage", "=", "internal"),
            ("location_id", "child_of", source.id),
            ("quantity", ">", 0),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "product_id",
            "location_id",
            "quantity",
            "reserved_quantity",
        ]
