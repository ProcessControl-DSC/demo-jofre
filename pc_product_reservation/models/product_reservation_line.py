# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductReservationLine(models.Model):
    _name = 'product.reservation.line'
    _description = 'Línea de reserva de producto'
    _inherit = ['pos.load.mixin']
    _check_company_auto = True

    reservation_id = fields.Many2one(
        'product.reservation',
        string='Reserva',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        domain="[('sale_ok', '=', True)]",
    )
    product_qty = fields.Float(
        string='Cantidad',
        default=1.0,
        required=True,
    )
    price_unit = fields.Float(
        string='Precio unitario',
        digits='Product Price',
        compute='_compute_price_unit',
        store=True,
        readonly=False,
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Movimiento de stock',
        copy=False,
        readonly=True,
    )
    company_id = fields.Many2one(
        related='reservation_id.company_id',
        store=True,
    )
    product_uom_id = fields.Many2one(
        related='product_id.uom_id',
        string='Unidad de medida',
    )
    state = fields.Selection(
        related='reservation_id.state',
        string='Estado reserva',
        store=True,
    )

    # -------------------------------------------------------------------------
    # POS LOAD MIXIN
    # -------------------------------------------------------------------------

    @api.model
    def _load_pos_data_domain(self, data, config):
        # Load lines for reservations already loaded in POS
        reservation_ids = [r['id'] for r in data.get('product.reservation', [])]
        if not reservation_ids:
            return False
        return [('reservation_id', 'in', reservation_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            'id', 'reservation_id', 'product_id', 'product_qty',
            'price_unit', 'write_date',
        ]

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            if line.product_id:
                line.price_unit = line.product_id.lst_price
            else:
                line.price_unit = 0.0

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('product_qty')
    def _check_product_qty(self):
        for line in self:
            if line.product_qty <= 0:
                raise ValidationError(
                    _('La cantidad reservada debe ser mayor que cero.')
                )
