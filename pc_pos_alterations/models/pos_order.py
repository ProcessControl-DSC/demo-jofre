# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from datetime import timedelta, datetime, time
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    repair_ids = fields.One2many(
        'repair.order',
        'pos_order_id',
        string='Reparaciones (Arreglos)',
    )
    has_alterations = fields.Boolean(
        string='Tiene arreglos',
        compute='_compute_has_alterations',
        store=True,
    )

    @api.depends('repair_ids')
    def _compute_has_alterations(self):
        for order in self:
            order.has_alterations = bool(order.repair_ids)

    def _process_alterations_after_payment(self):
        """Procesa los arreglos asociados tras la confirmación del pago.

        Busca líneas de arreglo en el pedido (líneas cuyo producto pertenece a la
        categoría POS de arreglos) y crea los registros repair.order correspondientes.
        """
        self.ensure_one()
        alteration_lines = self.lines.filtered(lambda l: l.is_alteration)
        if not alteration_lines:
            return

        AlterationType = self.env['alteration.type']
        RepairOrder = self.env['repair.order']

        warehouse = False
        if self.config_id.picking_type_id and self.config_id.picking_type_id.warehouse_id:
            warehouse = self.config_id.picking_type_id.warehouse_id

        # Buscar el picking type de reparación del almacén
        repair_picking_type = False
        if warehouse:
            repair_picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'repair_operation'),
                ('warehouse_id', '=', warehouse.id),
            ], limit=1)

        if not repair_picking_type:
            _logger.warning(
                'No se encontró tipo de operación de reparación para el almacén %s',
                warehouse.name if warehouse else 'N/A'
            )
            return

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

            # Calcular schedule_date como datetime a partir de date_promised
            if date_promised:
                try:
                    schedule_dt = datetime.combine(
                        fields.Date.from_string(date_promised),
                        time(18, 0, 0)
                    )
                except Exception:
                    schedule_dt = fields.Datetime.now() + timedelta(
                        days=alt_type.default_duration_days or 3
                    )
            else:
                schedule_dt = fields.Datetime.now() + timedelta(
                    days=alt_type.default_duration_days or 3
                )

            # Construir las notas internas con información del arreglo
            garment_name = garment_line.product_id.display_name if garment_line else ''
            notes_parts = []
            if alt_type.name:
                notes_parts.append(f'<b>Tipo de arreglo:</b> {alt_type.name}')
            if garment_name:
                notes_parts.append(f'<b>Prenda:</b> {garment_name}')
            if description:
                notes_parts.append(f'<b>Descripción:</b> {description}')
            delivery_label = 'Recogida en tienda' if delivery_method == 'pickup_store' else 'Envío a domicilio'
            notes_parts.append(f'<b>Método de entrega:</b> {delivery_label}')
            internal_notes = '<br/>'.join(notes_parts)

            # Producto a reparar: la prenda del cliente
            product_to_repair = garment_line.product_id if garment_line else False

            vals = {
                'product_id': product_to_repair.id if product_to_repair else False,
                'partner_id': self.partner_id.id if self.partner_id else False,
                'picking_type_id': repair_picking_type.id,
                'schedule_date': schedule_dt,
                'internal_notes': internal_notes,
                'user_id': self.user_id.id or self.env.user.id,
                'company_id': warehouse.company_id.id,
                'pos_order_id': self.id,
                'pos_order_line_id': garment_line.id if garment_line else False,
                'alteration_line_id': alt_line.id,
                'alteration_type_id': alt_type.id,
                'delivery_method': delivery_method,
            }

            try:
                repair = RepairOrder.create(vals)
                # Confirmar la reparación automáticamente
                repair.action_validate()
                # Iniciar la reparación automáticamente
                repair.action_repair_start()
            except Exception as e:
                _logger.error(
                    'Error al crear reparación para pedido %s, línea %s: %s',
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
