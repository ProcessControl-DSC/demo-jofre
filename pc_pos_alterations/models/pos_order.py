# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    alteration_ids = fields.One2many(
        'pos.alteration',
        'pos_order_id',
        string='Arreglos',
    )
    has_alterations = fields.Boolean(
        string='Tiene arreglos',
        compute='_compute_has_alterations',
        store=True,
    )

    @api.depends('alteration_ids')
    def _compute_has_alterations(self):
        for order in self:
            order.has_alterations = bool(order.alteration_ids)

    def _process_alterations_after_payment(self):
        """Procesa los arreglos asociados tras la confirmación del pago.

        Busca líneas de arreglo en el pedido (líneas cuyo producto pertenece a la
        categoría POS de arreglos) y crea los registros pos.alteration correspondientes.
        """
        self.ensure_one()
        alteration_lines = self.lines.filtered(lambda l: l.is_alteration)
        if not alteration_lines:
            return

        AlterationType = self.env['alteration.type']
        PosAlteration = self.env['pos.alteration']

        warehouse = False
        if self.config_id.picking_type_id and self.config_id.picking_type_id.warehouse_id:
            warehouse = self.config_id.picking_type_id.warehouse_id

        for alt_line in alteration_lines:
            # Buscar el tipo de arreglo por el producto
            alt_type = AlterationType.search([
                ('product_id', '=', alt_line.product_id.id),
            ], limit=1)
            if not alt_type:
                _logger.warning(
                    'No se encontró tipo de arreglo para el producto %s en el pedido %s',
                    alt_line.product_id.display_name, self.name
                )
                continue

            # La línea de la prenda es la referenciada por alteration_for_line_id
            garment_line = alt_line.alteration_for_line_id

            # Parsear los datos extra del arreglo almacenados en customer_note
            # Formato: "notes|date_promised|delivery_method"
            description = alt_line.customer_note or ''
            date_promised = False
            delivery_method = 'pickup_store'

            if description and '|' in description:
                parts = description.split('|')
                description = parts[0] if len(parts) > 0 else ''
                if len(parts) > 1 and parts[1]:
                    try:
                        date_promised = parts[1]
                    except Exception:
                        pass
                if len(parts) > 2 and parts[2]:
                    delivery_method = parts[2]

            if not date_promised:
                date_promised = fields.Date.context_today(self) + timedelta(
                    days=alt_type.default_duration_days or 3
                )

            vals = {
                'pos_order_id': self.id,
                'pos_order_line_id': garment_line.id if garment_line else False,
                'alteration_line_id': alt_line.id,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'product_id': garment_line.product_id.id if garment_line else False,
                'alteration_type_id': alt_type.id,
                'description': description,
                'user_id': self.user_id.id or self.env.user.id,
                'warehouse_id': warehouse.id if warehouse else False,
                'date_promised': date_promised,
                'cost': alt_type.product_id.list_price if alt_type.product_id else 0,
                'delivery_method': delivery_method,
            }

            try:
                alteration = PosAlteration.create(vals)
                alteration.action_start()
            except Exception as e:
                _logger.error(
                    'Error al crear arreglo para pedido %s, línea %s: %s',
                    self.name, alt_line.id, str(e)
                )

    @api.model
    def _process_order(self, order, existing_order):
        """Override para procesar arreglos tras la creación del pedido."""
        order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)
        try:
            pos_order._process_alterations_after_payment()
        except Exception as e:
            _logger.error(
                'Error procesando arreglos del pedido %s: %s',
                pos_order.name, str(e)
            )
        return order_id
