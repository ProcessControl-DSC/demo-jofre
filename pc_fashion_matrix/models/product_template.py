from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fashion_season_id = fields.Many2one('fashion.season', string='Temporada')
    fashion_gender = fields.Selection([
        ('man', 'Hombre'),
        ('woman', 'Mujer'),
        ('kids', 'Niños'),
        ('baby', 'Bebé'),
        ('unisex', 'Unisex'),
    ], string='Género')
    fashion_family_id = fields.Many2one('fashion.product.family', string='Familia')
    fashion_subfamily_id = fields.Many2one(
        'fashion.product.family', string='Subfamilia',
        domain="[('parent_id', '=', fashion_family_id)]",
    )

    def _get_template_matrix(self, **kwargs):
        """Extiende la matriz estándar con información de coste y PVP."""
        matrix = super()._get_template_matrix(**kwargs)
        matrix['cost_price'] = self.standard_price
        matrix['sale_price'] = self.list_price
        matrix['product_template_id'] = self.id
        return matrix
