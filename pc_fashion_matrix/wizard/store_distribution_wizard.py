from odoo import models, fields


class StoreDistributionWizard(models.TransientModel):
    _name = 'store.distribution.wizard'
    _description = 'Ajuste manual de distribución por tienda'

    purchase_order_id = fields.Many2one('purchase.order')
    distribution_profile_id = fields.Many2one('store.distribution.profile')
