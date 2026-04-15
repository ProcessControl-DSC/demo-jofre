# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data_fields(self, config_id):
        """Extend POS data loading to include warehouse info."""
        result = super()._load_pos_data_fields(config_id)
        return result
