# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    alteration_for_line_id = fields.Many2one(
        'pos.order.line',
        string='Arreglo para línea',
        help='Línea de prenda a la que se asocia este arreglo.',
        index='btree_not_null',
    )
    is_alteration = fields.Boolean(
        string='Es arreglo',
        compute='_compute_is_alteration',
        store=True,
    )

    @api.depends('product_id', 'product_id.pos_categ_ids')
    def _compute_is_alteration(self):
        arreglos_categ = self.env.ref(
            'pc_pos_alterations.pos_category_arreglos', raise_if_not_found=False
        )
        for line in self:
            if arreglos_categ and line.product_id:
                line.is_alteration = arreglos_categ in line.product_id.pos_categ_ids
            else:
                line.is_alteration = False

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['alteration_for_line_id', 'is_alteration']
        return params
