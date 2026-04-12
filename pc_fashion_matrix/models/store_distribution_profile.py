# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StoreDistributionProfile(models.Model):
    _name = 'store.distribution.profile'
    _description = 'Store Distribution Profile'
    _order = 'name'

    name = fields.Char(
        string='Profile Name',
        required=True,
        help='Descriptive name for this distribution profile',
    )
    line_ids = fields.One2many(
        comodel_name='store.distribution.profile.line',
        inverse_name='profile_id',
        string='Store Lines',
    )
    total_percentage = fields.Float(
        string='Total %',
        compute='_compute_total_percentage',
        store=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    @api.depends('line_ids.percentage')
    def _compute_total_percentage(self):
        for profile in self:
            profile.total_percentage = sum(profile.line_ids.mapped('percentage'))

    @api.constrains('line_ids')
    def _check_total_percentage(self):
        for profile in self:
            total = sum(profile.line_ids.mapped('percentage'))
            if profile.line_ids and abs(total - 100.0) > 0.01:
                raise ValidationError(
                    "The sum of percentages in the distribution profile "
                    f"'{profile.name}' must equal 100%%. Current total: {total:.2f}%%"
                )


class StoreDistributionProfileLine(models.Model):
    _name = 'store.distribution.profile.line'
    _description = 'Store Distribution Profile Line'
    _order = 'percentage desc'

    profile_id = fields.Many2one(
        comodel_name='store.distribution.profile',
        string='Profile',
        required=True,
        ondelete='cascade',
    )
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Store / Warehouse',
        required=True,
    )
    percentage = fields.Float(
        string='Percentage (%)',
        required=True,
        help='Percentage of the total quantity allocated to this store',
    )

    _sql_constraints = [
        (
            'percentage_positive',
            'CHECK(percentage > 0)',
            'The percentage must be greater than zero.',
        ),
        (
            'warehouse_profile_unique',
            'UNIQUE(profile_id, warehouse_id)',
            'Each warehouse can only appear once per profile.',
        ),
    ]
