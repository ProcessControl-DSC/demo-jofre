from odoo import models, fields


class FashionProductFamily(models.Model):
    _name = 'fashion.product.family'
    _description = 'Familia de producto moda'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    parent_id = fields.Many2one('fashion.product.family', string='Subfamilia de')
    child_ids = fields.One2many('fashion.product.family', 'parent_id', string='Subfamilias')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'El nombre de familia debe ser único.'),
    ]
