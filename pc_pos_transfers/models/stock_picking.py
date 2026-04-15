# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

import logging
import re
from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create_transfer_from_pos(self, vals):
        """Create an internal transfer requested from POS.

        :param vals: dict with keys:
            - product_id: int, product.product id
            - qty: float, quantity to transfer
            - source_warehouse_id: int, source stock.warehouse id (optional if source_warehouse_name given)
            - source_warehouse_name: str, source warehouse name (resolved to id if source_warehouse_id not given)
            - dest_warehouse_id: int, destination stock.warehouse id
            - user_name: str, name of the POS employee requesting
        :return: dict with picking info {id, name, state}
        """
        product_id = vals.get('product_id')
        product_template_id = vals.get('product_template_id')
        qty = vals.get('qty', 1)
        source_wh_id = vals.get('source_warehouse_id')
        dest_wh_id = vals.get('dest_warehouse_id')
        user_name = vals.get('user_name', '')

        # Resolve product by name if no ID provided
        if not product_id and not product_template_id and vals.get("product_name"):
            product_name = vals["product_name"]
            # Try exact match first, then ilike
            template = self.env["product.template"].search([
                ("name", "ilike", product_name),
            ], limit=1)
            if template and template.product_variant_ids:
                product_id = template.product_variant_ids[0].id
                product_template_id = template.id

        # Resolve product_id from template if not provided directly
        if not product_id and product_template_id:
            template = self.env['product.template'].browse(product_template_id)
            if template.exists() and template.product_variant_ids:
                product_id = template.product_variant_ids[0].id

        # Resolve source warehouse by name if ID not provided
        if not source_wh_id and vals.get('source_warehouse_name'):
            source_wh = self.env['stock.warehouse'].search([
                ('name', '=', vals['source_warehouse_name']),
            ], limit=1)
            if source_wh:
                source_wh_id = source_wh.id

        if not product_id or not source_wh_id or not dest_wh_id:
            raise UserError(_("Faltan datos obligatorios para crear el traslado."))

        if source_wh_id == dest_wh_id:
            raise UserError(_("El almacén de origen y destino no pueden ser el mismo."))

        if qty <= 0:
            raise UserError(_("La cantidad debe ser mayor que cero."))

        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            raise UserError(_("El producto no existe."))

        source_wh = self.env['stock.warehouse'].browse(source_wh_id)
        dest_wh = self.env['stock.warehouse'].browse(dest_wh_id)

        if not source_wh.exists() or not dest_wh.exists():
            raise UserError(_("Almacén de origen o destino no encontrado."))

        # Use the internal transfer type of the DESTINATION warehouse
        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_wh.id),
            ('code', '=', 'internal'),
        ], limit=1)

        if not picking_type:
            raise UserError(
                _("No se ha encontrado un tipo de operación de traslado interno "
                  "para el almacén %s.", dest_wh.name)
            )

        source_location = source_wh.lot_stock_id
        dest_location = dest_wh.lot_stock_id

        if not source_location or not dest_location:
            raise UserError(_("No se han encontrado las ubicaciones de stock."))

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': "POS Transfer - %s" % dest_wh.name,
            'note': "Solicitado desde TPV por %s" % user_name,
            'move_ids': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'picked': False,
            })],
        }

        picking = self.create(picking_vals)
        picking.action_confirm()

        _logger.info(
            "POS Transfer created: %s (product: %s, qty: %s, from: %s to: %s, by: %s)",
            picking.name, product.display_name, qty,
            source_wh.name, dest_wh.name, user_name,
        )

        return {
            'id': picking.id,
            'name': picking.name,
            'state': picking.state,
        }

    @api.model
    def get_transfers_for_pos(self, warehouse_id, state_filter=False):
        """Get incoming internal transfers for a warehouse.

        Returns transfers where the destination is this warehouse's stock location.

        :param warehouse_id: int, stock.warehouse id
        :param state_filter: str or False, filter by mapped state:
            'pending' = draft/waiting/confirmed
            'shipped' = assigned
            'received' = done
            'all' or False = all states
        :return: list of dicts with transfer info
        """
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        if not warehouse.exists():
            return []

        dest_location = warehouse.lot_stock_id
        if not dest_location:
            return []

        # Find the internal picking type for this warehouse
        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', warehouse.id),
            ('code', '=', 'internal'),
        ], limit=1)

        if not picking_type:
            return []

        domain = [
            ('picking_type_id', '=', picking_type.id),
            ('location_dest_id', '=', dest_location.id),
            # Only show transfers where source is from a DIFFERENT warehouse
            ('location_id', '!=', dest_location.id),
        ]

        # Apply state filter
        if state_filter == 'pending':
            domain.append(('state', 'in', ['draft', 'waiting', 'confirmed']))
        elif state_filter == 'shipped':
            domain.append(('state', '=', 'assigned'))
        elif state_filter == 'received':
            domain.append(('state', '=', 'done'))
        elif state_filter and state_filter != 'all':
            domain.append(('state', '=', state_filter))
        else:
            # Exclude cancelled by default when showing all
            domain.append(('state', '!=', 'cancel'))

        pickings = self.search(domain, order='create_date desc', limit=100)

        result = []
        for picking in pickings:
            # Get the source warehouse name from the source location
            source_wh = self.env['stock.warehouse'].search([
                ('lot_stock_id', '=', picking.location_id.id),
            ], limit=1)
            source_wh_name = source_wh.name if source_wh else picking.location_id.display_name

            # Get product info from moves
            product_info = []
            for move in picking.move_ids:
                product_info.append({
                    'product_id': move.product_id.id,
                    'product_name': move.product_id.display_name,
                    'qty_demanded': move.product_uom_qty,
                    'qty_done': move.quantity,
                })

            # Map state to POS display state
            pos_state = self._map_picking_state_to_pos(picking.state)

            result.append({
                'id': picking.id,
                'name': picking.name,
                'origin': picking.origin or '',
                'state': picking.state,
                'pos_state': pos_state,
                'source_warehouse': source_wh_name,
                'products': product_info,
                'date': picking.scheduled_date.isoformat() if picking.scheduled_date else '',
                'create_date': picking.create_date.isoformat() if picking.create_date else '',
                'note': re.sub(r'<[^>]+>', '', picking.note or '').strip(),
            })

        return result

    @api.model
    def _map_picking_state_to_pos(self, state):
        """Map stock.picking state to POS display state."""
        mapping = {
            'draft': 'pending',
            'waiting': 'pending',
            'confirmed': 'pending',
            'assigned': 'shipped',
            'done': 'received',
            'cancel': 'cancelled',
        }
        return mapping.get(state, 'pending')

    @api.model
    def receive_transfer_from_pos(self, picking_id):
        """Validate an incoming transfer from POS (receive goods).

        Sets all move quantities to demanded and validates the picking.

        :param picking_id: int, stock.picking id
        :return: dict with success status
        """
        picking = self.browse(picking_id)
        if not picking.exists():
            raise UserError(_("El traslado no existe."))

        if picking.state == 'done':
            return {'success': True, 'message': _("El traslado ya estaba recibido.")}

        if picking.state == 'cancel':
            raise UserError(_("No se puede recepcionar un traslado cancelado."))

        if picking.state not in ('assigned',):
            raise UserError(
                _("El traslado no está listo para recepcionar. "
                  "Estado actual: %s", picking.state)
            )

        try:
            # Set quantities done on all moves
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True

            # Validate the picking — handle potential backorder wizard
            result = picking.with_context(
                skip_backorder=True,
                picking_ids_not_to_backorder=picking.ids,
            ).button_validate()

            # If button_validate returns a wizard action, we need to confirm it
            if isinstance(result, dict) and result.get('res_model'):
                wizard_model = result['res_model']
                wizard_id = result.get('res_id')
                if wizard_id:
                    wizard = self.env[wizard_model].browse(wizard_id)
                    if hasattr(wizard, 'process'):
                        wizard.process()
                    elif hasattr(wizard, 'process_cancel_backorder'):
                        wizard.process_cancel_backorder()

            _logger.info("POS Transfer received: %s", picking.name)

            return {
                'success': True,
                'message': _("Traslado %s recibido correctamente.", picking.name),
            }
        except Exception as e:
            _logger.error("Error receiving transfer %s from POS: %s", picking.name, str(e))
            raise UserError(
                _("Error al recepcionar el traslado: %s", str(e))
            )
