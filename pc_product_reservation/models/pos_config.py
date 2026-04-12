# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    module_pc_product_reservation = fields.Boolean(
        string='Reservas de producto',
        default=True,
        help='Permite reservar productos para clientes desde el TPV.',
    )
