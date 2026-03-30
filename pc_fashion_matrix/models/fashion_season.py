from odoo import models, fields, api


class FashionSeason(models.Model):
    _name = 'fashion.season'
    _description = 'Temporada de moda'
    _order = 'year desc, season_type desc'

    name = fields.Char(compute='_compute_name', store=True)
    code = fields.Char(required=True)
    season_type = fields.Selection([
        ('V', 'Verano / Spring-Summer'),
        ('I', 'Invierno / Fall-Winter'),
    ], required=True)
    year = fields.Integer(required=True)
    active = fields.Boolean(default=True)

    @api.depends('season_type', 'year')
    def _compute_name(self):
        labels = {'V': 'Verano', 'I': 'Invierno'}
        for rec in self:
            rec.name = f"{labels.get(rec.season_type, '')} {rec.year}" if rec.year else rec.code

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'El código de temporada debe ser único.'),
    ]
