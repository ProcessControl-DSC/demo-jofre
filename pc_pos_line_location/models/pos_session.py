from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        if config.allow_line_location_selection:
            data += ["stock.location", "stock.quant"]
        return data
