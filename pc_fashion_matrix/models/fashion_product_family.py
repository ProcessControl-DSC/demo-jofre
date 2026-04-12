# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FashionProductFamily(models.Model):
    _name = 'fashion.product.family'
    _description = 'Fashion Product Family'
    _order = 'name'

    name = fields.Char(
        string='Family',
        required=True,
        help='Product family name, e.g. Pantalones, Camisas, Chaquetas',
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the family',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        (
            'code_unique',
            'UNIQUE(code)',
            'The family code must be unique.',
        ),
    ]
