# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model_create_multi
    def create(self, vals_list):
        """Al crear un nuevo almacén, crea automáticamente la ubicación Taller de Costura."""
        warehouses = super().create(vals_list)
        Location = self.env['stock.location']
        for wh in warehouses:
            existing = Location.search([
                ('name', '=', 'Taller de Costura'),
                ('location_id', '=', wh.lot_stock_id.id),
                ('usage', '=', 'internal'),
            ], limit=1)
            if not existing:
                Location.create({
                    'name': 'Taller de Costura',
                    'usage': 'internal',
                    'location_id': wh.lot_stock_id.id,
                    'company_id': wh.company_id.id,
                })
        return warehouses
