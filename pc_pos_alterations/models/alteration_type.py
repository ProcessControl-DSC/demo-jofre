# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AlterationType(models.Model):
    _name = 'alteration.type'
    _description = 'Tipo de Arreglo'
    _inherit = ['pos.load.mixin']
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    code = fields.Char(string='Código', required=True)
    product_id = fields.Many2one(
        'product.product',
        string='Producto de arreglo',
        required=True,
        domain=[('type', '=', 'service')],
        help='Producto de tipo servicio que se añadirá como línea en el pedido TPV.',
    )
    default_duration_days = fields.Integer(string='Días estimados', default=3)
    description = fields.Text(string='Descripción')
    active = fields.Boolean(string='Activo', default=True)

    _constraints = [
        models.Constraint(
            'UNIQUE(code)',
            'El código del tipo de arreglo debe ser único.',
        ),
    ]

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('active', '=', True)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            'id', 'name', 'code', 'product_id',
            'default_duration_days', 'description', 'active', 'write_date',
        ]
