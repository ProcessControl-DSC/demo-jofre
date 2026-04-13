# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    pos_order_id = fields.Many2one(
        'pos.order',
        string='Pedido TPV',
        readonly=True,
        index='btree_not_null',
        copy=False,
    )
    pos_order_line_id = fields.Many2one(
        'pos.order.line',
        string='Línea de prenda (TPV)',
        readonly=True,
        copy=False,
    )
    alteration_line_id = fields.Many2one(
        'pos.order.line',
        string='Línea de arreglo (TPV)',
        readonly=True,
        copy=False,
    )
    alteration_type_id = fields.Many2one(
        'alteration.type',
        string='Tipo de arreglo',
        tracking=True,
    )
    delivery_method = fields.Selection([
        ('pickup_store', 'Recogida en tienda'),
        ('ship_customer', 'Envío a domicilio'),
    ], string='Método de entrega', default='pickup_store')

    # --- Smart buttons ---

    def action_view_pos_order(self):
        """Abre el pedido TPV asociado a esta reparación."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'form',
            'res_id': self.pos_order_id.id,
            'target': 'current',
        }

    # --- Métodos RPC llamados desde el POS ---

    @api.model
    def get_repairs_for_pos(self, warehouse_id, states=None):
        """Obtiene las reparaciones de una tienda para mostrar en el TPV.

        Filtra por el picking_type_id de tipo reparación del almacén indicado.
        """
        # Buscar el picking type de reparación del almacén
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'repair_operation'),
            ('warehouse_id', '=', warehouse_id),
        ], limit=1)
        if not picking_type:
            return []

        domain = [('picking_type_id', '=', picking_type.id)]
        if states:
            domain.append(('state', 'in', states))
        else:
            domain.append(('state', '!=', 'cancel'))

        repairs = self.search(domain, order='schedule_date asc, id desc', limit=100)
        result = []
        for r in repairs:
            schedule_str = ''
            if r.schedule_date:
                schedule_str = str(r.schedule_date.date())

            result.append({
                'id': r.id,
                'name': r.name,
                'state': r.state,
                'partner_name': r.partner_id.name or '',
                'partner_phone': r.partner_id.phone or r.partner_id.mobile or '',
                'product_name': r.product_id.display_name if r.product_id else '',
                'alteration_type': r.alteration_type_id.name if r.alteration_type_id else '',
                'alteration_type_code': r.alteration_type_id.code if r.alteration_type_id else '',
                'description': r.internal_notes or '',
                'date_promised': schedule_str,
                'delivery_method': r.delivery_method or '',
                'is_overdue': (
                    r.state in ('draft', 'confirmed', 'under_repair')
                    and r.schedule_date
                    and r.schedule_date.date() < fields.Date.context_today(self)
                ),
                'user_name': r.user_id.name if r.user_id else '',
                'warehouse_name': picking_type.warehouse_id.name if picking_type.warehouse_id else '',
            })
        return result

    @api.model
    def change_repair_state_from_pos(self, repair_id, action):
        """Cambia el estado de una reparación desde el TPV.

        Args:
            repair_id: ID de la repair.order
            action: 'confirm', 'start', 'end', 'cancel'

        Returns:
            dict con id, name, state de la reparación actualizada.
        """
        repair = self.browse(repair_id)
        if not repair.exists():
            raise UserError(_('Reparación no encontrada.'))

        if action == 'confirm':
            repair.action_validate()
        elif action == 'start':
            repair.action_repair_start()
        elif action == 'end':
            repair.action_repair_end()
        elif action == 'cancel':
            repair.action_repair_cancel()
        else:
            raise UserError(_('Acción no válida: %s', action))

        return {
            'id': repair.id,
            'name': repair.name,
            'state': repair.state,
        }

    @api.model
    def search_repairs_from_pos(self, warehouse_id, search_term):
        """Busca reparaciones por nombre de cliente o referencia."""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'repair_operation'),
            ('warehouse_id', '=', warehouse_id),
        ], limit=1)
        if not picking_type:
            return []

        domain = [
            ('picking_type_id', '=', picking_type.id),
            ('state', '!=', 'cancel'),
            '|',
            ('name', 'ilike', search_term),
            ('partner_id.name', 'ilike', search_term),
        ]
        repairs = self.search(domain, order='schedule_date asc, id desc', limit=50)
        result = []
        for r in repairs:
            schedule_str = ''
            if r.schedule_date:
                schedule_str = str(r.schedule_date.date())

            result.append({
                'id': r.id,
                'name': r.name,
                'state': r.state,
                'partner_name': r.partner_id.name or '',
                'partner_phone': r.partner_id.phone or r.partner_id.mobile or '',
                'product_name': r.product_id.display_name if r.product_id else '',
                'alteration_type': r.alteration_type_id.name if r.alteration_type_id else '',
                'description': r.internal_notes or '',
                'date_promised': schedule_str,
                'delivery_method': r.delivery_method or '',
                'is_overdue': (
                    r.state in ('draft', 'confirmed', 'under_repair')
                    and r.schedule_date
                    and r.schedule_date.date() < fields.Date.context_today(self)
                ),
            })
        return result
