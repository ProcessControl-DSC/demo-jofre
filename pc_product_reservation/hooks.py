# -*- coding: utf-8 -*-


def _create_reservation_locations(env):
    """Create 'Reservas Clientes' location in each existing warehouse on module install."""
    warehouses = env['stock.warehouse'].search([])
    for wh in warehouses:
        _create_single_reservation_location(env, wh)


def _create_single_reservation_location(env, warehouse):
    """Create the reservation location as a child of the warehouse stock location."""
    location_name = 'Reservas Clientes'
    existing = env['stock.location'].sudo().search([
        ('name', '=', location_name),
        ('location_id', '=', warehouse.lot_stock_id.id),
        ('usage', '=', 'internal'),
    ], limit=1)
    if not existing:
        env['stock.location'].sudo().create({
            'name': location_name,
            'usage': 'internal',
            'location_id': warehouse.lot_stock_id.id,
            'company_id': warehouse.company_id.id,
        })
