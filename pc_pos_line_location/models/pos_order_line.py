from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        domain="[('usage', '=', 'internal')]",
        index=True,
        help=(
            "Stock location chosen by the cashier as source of this line. "
            "When set, it overrides the default removal strategy when the "
            "picking is generated."
        ),
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if "location_id" not in fields:
            fields.append("location_id")
        return fields
