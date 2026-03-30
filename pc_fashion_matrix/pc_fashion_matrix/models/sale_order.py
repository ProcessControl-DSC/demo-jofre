import json

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fashion_season_id = fields.Many2one('fashion.season', string='Temporada')
    fashion_gender = fields.Selection([
        ('man', 'Hombre'),
        ('woman', 'Mujer'),
        ('kids', 'Niños'),
        ('baby', 'Bebé'),
        ('unisex', 'Unisex'),
    ], string='Género')
    fashion_family_id = fields.Many2one('fashion.product.family', string='Familia')
    distribution_profile_id = fields.Many2one(
        'store.distribution.profile', string='Perfil distribución',
    )
    distribution_data = fields.Text(
        string='Datos de distribución',
        help='JSON con la distribución por tienda generada desde el grid.',
    )

    @api.onchange('grid')
    def _apply_grid(self):
        """Extiende _apply_grid para almacenar la distribución por tienda."""
        res = super()._apply_grid()
        if self.grid and self.grid_update:
            grid = json.loads(self.grid)
            if grid.get('store_distribution'):
                self.distribution_data = json.dumps(grid['store_distribution'])
        return res
