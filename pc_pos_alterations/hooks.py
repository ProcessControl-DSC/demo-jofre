# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.


def _create_workshop_locations(env):
    """Post-init hook: crea la ubicación 'Taller de Costura' en cada almacén existente."""
    warehouses = env['stock.warehouse'].search([])
    Location = env['stock.location']
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
