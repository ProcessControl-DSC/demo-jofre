# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import api, fields, models, _
from odoo.exceptions import UserError


FASHION_GENDER_SELECTION = [
    ('man', 'Man'),
    ('woman', 'Woman'),
    ('boy', 'Boy'),
    ('girl', 'Girl'),
    ('baby', 'Baby'),
    ('unisex', 'Unisex'),
]


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fashion_season_id = fields.Many2one(
        comodel_name='fashion.season',
        string='Season',
        help='Fashion season for this purchase order',
    )
    distribution_profile_id = fields.Many2one(
        comodel_name='store.distribution.profile',
        string='Distribution Profile',
        help='Store distribution profile to use when distributing stock to stores',
    )
    fashion_gender = fields.Selection(
        selection=FASHION_GENDER_SELECTION,
        string='Gender',
    )

    @api.model
    def action_fashion_matrix_add_lines(self, order_id, lines_data):
        """Add purchase order lines from the fashion matrix dialog.

        Called from the OWL component via RPC.

        :param order_id: int - purchase.order id
        :param lines_data: list of dicts with 'product_id' and 'product_qty'
        :returns: True on success
        """
        order = self.browse(order_id)
        if not order.exists():
            raise UserError(_("Purchase order not found."))

        POLine = self.env['purchase.order.line']
        for line_data in lines_data:
            product = self.env['product.product'].browse(line_data['product_id'])
            if not product.exists():
                continue

            qty = line_data.get('product_qty', 0)
            if qty <= 0:
                continue

            # Check if a line for this product already exists on the order
            existing_line = order.order_line.filtered(
                lambda l: l.product_id.id == product.id
            )
            if existing_line:
                # Update existing line quantity
                existing_line[0].product_qty += qty
            else:
                # Retrieve supplier price info if available
                price_unit = 0.0
                supplierinfo = product.product_tmpl_id._select_seller(
                    partner_id=order.partner_id,
                    quantity=qty,
                    uom_id=product.uom_po_id or product.uom_id,
                    date=order.date_order and order.date_order.date(),
                )
                if supplierinfo:
                    price_unit = supplierinfo.price
                else:
                    price_unit = product.standard_price

                # Determine taxes from the fiscal position
                taxes = product.supplier_taxes_id
                if order.fiscal_position_id:
                    taxes = order.fiscal_position_id.map_tax(taxes)

                line_vals = {
                    'order_id': order.id,
                    'product_id': product.id,
                    'name': product.display_name,
                    'product_qty': qty,
                    'product_uom': (product.uom_po_id or product.uom_id).id,
                    'price_unit': price_unit,
                    'taxes_id': [(6, 0, taxes.ids)],
                    'date_planned': order.date_planned or fields.Datetime.now(),
                }
                POLine.create(line_vals)

        return True

    def action_open_fashion_matrix(self):
        """Open the fashion matrix dialog as a client action.

        This returns a client action that the OWL component will intercept
        to render the enhanced fashion matrix dialog.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'pc_fashion_matrix.open_fashion_matrix',
            'name': _('Fashion Matrix'),
            'params': {
                'purchase_order_id': self.id,
                'season_id': self.fashion_season_id.id or False,
                'gender': self.fashion_gender or False,
                'partner_id': self.partner_id.id or False,
                'distribution_profile_id': self.distribution_profile_id.id or False,
            },
        }

    def action_distribute_to_stores(self):
        """Create internal transfers from central warehouse to store warehouses
        based on the distribution profile percentages.

        Uses the Largest Remainder Method (Hund) to ensure integer quantities
        that sum exactly to the total for each product line.
        """
        self.ensure_one()

        if self.state not in ('purchase', 'done'):
            raise UserError(_(
                "You can only distribute stock from a confirmed purchase order."
            ))

        if not self.distribution_profile_id:
            raise UserError(_(
                "Please select a Distribution Profile before distributing to stores."
            ))

        profile = self.distribution_profile_id
        if not profile.line_ids:
            raise UserError(_(
                "The distribution profile '%s' has no store lines configured.",
                profile.name,
            ))

        # Central warehouse is the PO destination (picking_type_id.warehouse_id)
        central_warehouse = self.picking_type_id.warehouse_id
        if not central_warehouse:
            raise UserError(_(
                "Cannot determine the central warehouse from the purchase order."
            ))

        # Build percentages dict
        percentages = {}
        for line in profile.line_ids:
            if line.warehouse_id.id == central_warehouse.id:
                continue  # Skip central warehouse in distribution
            percentages[line.warehouse_id.id] = line.percentage

        if not percentages:
            raise UserError(_(
                "No target stores found in the distribution profile "
                "(the central warehouse is excluded from distribution)."
            ))

        # Normalize percentages to 100% among target stores
        total_pct = sum(percentages.values())
        if total_pct <= 0:
            raise UserError(_("Distribution percentages must be positive."))
        normalized = {wh_id: (pct / total_pct) * 100 for wh_id, pct in percentages.items()}

        # Prepare picking data per warehouse
        picking_type_internal = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', central_warehouse.id),
        ], limit=1)

        if not picking_type_internal:
            raise UserError(_(
                "No internal transfer operation type found for warehouse '%s'.",
                central_warehouse.name,
            ))

        pickings_data = {}  # warehouse_id -> list of move vals

        for po_line in self.order_line:
            if not po_line.product_id or po_line.product_qty <= 0:
                continue

            total_qty = int(po_line.product_qty)
            distribution = self._distribute_hund(total_qty, normalized)

            for wh_id, qty in distribution.items():
                if qty <= 0:
                    continue
                if wh_id not in pickings_data:
                    pickings_data[wh_id] = []

                warehouse = self.env['stock.warehouse'].browse(wh_id)
                pickings_data[wh_id].append({
                    'name': po_line.product_id.display_name,
                    'product_id': po_line.product_id.id,
                    'product_uom_qty': qty,
                    'product_uom': po_line.product_uom.id,
                    'location_id': central_warehouse.lot_stock_id.id,
                    'location_dest_id': warehouse.lot_stock_id.id,
                })

        # Create pickings
        created_pickings = self.env['stock.picking']
        for wh_id, move_vals_list in pickings_data.items():
            warehouse = self.env['stock.warehouse'].browse(wh_id)
            picking_vals = {
                'picking_type_id': picking_type_internal.id,
                'location_id': central_warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.lot_stock_id.id,
                'origin': _("Distribution from %s", self.name),
                'move_ids': [(0, 0, vals) for vals in move_vals_list],
            }
            picking = self.env['stock.picking'].create(picking_vals)
            created_pickings |= picking

        if not created_pickings:
            raise UserError(_(
                "No stock to distribute. All order lines have zero quantity."
            ))

        # Confirm the pickings
        created_pickings.action_confirm()

        # Return action to view the created pickings
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Store Distribution Transfers'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_pickings.ids)],
            'context': {'default_picking_type_id': picking_type_internal.id},
        }
        if len(created_pickings) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = created_pickings.id
        return action

    @api.model
    def _distribute_hund(self, total_qty, percentages):
        """Distribute total_qty among stores by percentages using the
        Largest Remainder Method (Ley de Hund / Hamilton method).

        :param total_qty: int - total units to distribute
        :param percentages: dict {store_id: percentage} where percentages
                           should sum to 100
        :returns: dict {store_id: integer_qty}
        """
        if not percentages or total_qty <= 0:
            return {s: 0 for s in percentages}

        # Calculate ideal quotas
        quotas = {s: total_qty * p / 100.0 for s, p in percentages.items()}

        # Floor each quota to get initial integer allocation
        result = {s: math.floor(q) for s, q in quotas.items()}

        # Calculate how many units still need to be distributed
        remainder = total_qty - sum(result.values())

        # Sort by fractional remainder descending, distribute one unit each
        sorted_by_remainder = sorted(
            quotas.items(),
            key=lambda x: x[1] - math.floor(x[1]),
            reverse=True,
        )

        for i in range(int(remainder)):
            if i < len(sorted_by_remainder):
                result[sorted_by_remainder[i][0]] += 1

        return result
