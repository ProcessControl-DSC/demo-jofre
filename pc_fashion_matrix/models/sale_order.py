# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fashion_season_id = fields.Many2one(
        comodel_name='fashion.season',
        string='Season',
        help='Fashion season for this sale order',
    )
