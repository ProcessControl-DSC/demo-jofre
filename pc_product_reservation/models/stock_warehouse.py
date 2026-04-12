# -*- coding: utf-8 -*-
from odoo import api, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model_create_multi
    def create(self, vals_list):
        """On new warehouse creation, automatically create the reservation location."""
        warehouses = super().create(vals_list)
        from odoo.addons.pc_product_reservation.hooks import _create_single_reservation_location
        for wh in warehouses:
            _create_single_reservation_location(self.env, wh)
        return warehouses
