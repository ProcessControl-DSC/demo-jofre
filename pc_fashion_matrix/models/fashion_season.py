# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FashionSeason(models.Model):
    _name = 'fashion.season'
    _description = 'Fashion Season'
    _order = 'date_start desc, name'

    name = fields.Char(
        string='Season',
        required=True,
        help='Season name, e.g. V2026 (Verano 2026), I2026 (Invierno 2026)',
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the season, e.g. SS26, FW26',
    )
    date_start = fields.Date(
        string='Start Date',
        required=True,
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _constraints = [
        models.Constraint(
            'UNIQUE(code)',
            'The season code must be unique.',
        ),
        models.Constraint(
            'CHECK(date_end >= date_start)',
            'The end date must be after the start date.',
        ),
    ]

    def name_get(self):
        return [(rec.id, f"[{rec.code}] {rec.name}") for rec in self]
