from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_line_location_selection = fields.Boolean(
        string="Select Source Location per Line",
        default=True,
        help=(
            "When enabled, the cashier can choose the source stock location "
            "for each product line added to the ticket. If stock is available "
            "in only one location, the system assigns it silently."
        ),
    )
