import json

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fashion_season_id = fields.Many2one('fashion.season', string='Temporada')
    fashion_gender = fields.Selection([
        ('man', 'Hombre'),
        ('woman', 'Mujer'),
        ('kids', 'Niños'),
        ('baby', 'Bebé'),
        ('unisex', 'Unisex'),
    ], string='Género')
    fashion_family_id = fields.Many2one('fashion.product.family', string='Familia')
    distribution_profile_id = fields.Many2one(
        'store.distribution.profile', string='Perfil distribución',
    )
    distribution_data = fields.Text(
        string='Datos de distribución',
        help='JSON con la distribución por tienda generada desde el grid.',
    )
    store_picking_ids = fields.One2many(
        'stock.picking', 'fashion_source_po_id',
        string='Transferencias a tiendas',
    )
    store_picking_count = fields.Integer(
        compute='_compute_store_picking_count',
    )

    @api.depends('store_picking_ids')
    def _compute_store_picking_count(self):
        for rec in self:
            rec.store_picking_count = len(rec.store_picking_ids)

    @api.onchange('grid')
    def _apply_grid(self):
        """Extiende _apply_grid para almacenar la distribución por tienda."""
        res = super()._apply_grid()
        if self.grid and self.grid_update:
            grid = json.loads(self.grid)
            if grid.get('store_distribution'):
                self.distribution_data = json.dumps(grid['store_distribution'])
        return res

    def action_create_store_transfers(self):
        """Crea transferencias internas desde almacén central a cada tienda."""
        self.ensure_one()
        if not self.distribution_data:
            return

        distribution = json.loads(self.distribution_data)
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']
        Warehouse = self.env['stock.warehouse']

        # Almacén origen = almacén del PO
        source_wh = self.picking_type_id.warehouse_id
        source_location = source_wh.lot_stock_id

        # Tipo de operación: transferencia interna del almacén origen
        int_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', source_wh.id),
            ('code', '=', 'internal'),
        ], limit=1)
        if not int_type:
            int_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
            ], limit=1)

        created_pickings = StockPicking
        for store_data in distribution:
            wh_id = store_data.get('warehouse_id')
            lines = store_data.get('lines', [])
            if not lines:
                continue

            dest_wh = Warehouse.browse(wh_id)
            dest_location = dest_wh.lot_stock_id

            picking = StockPicking.create({
                'picking_type_id': int_type.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'origin': self.name,
                'fashion_source_po_id': self.id,
            })

            for line in lines:
                product = self.env['product.product'].browse(line['product_id'])
                StockMove.create({
                    'name': product.display_name,
                    'product_id': product.id,
                    'product_uom_qty': line['qty'],
                    'product_uom': product.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': source_location.id,
                    'location_dest_id': dest_location.id,
                })

            picking.action_confirm()
            created_pickings |= picking

        return {
            'type': 'ir.actions.act_window',
            'name': 'Transferencias a tiendas',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_pickings.ids)],
        }

    def action_view_store_pickings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transferencias a tiendas',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.store_picking_ids.ids)],
        }


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fashion_source_po_id = fields.Many2one(
        'purchase.order', string='Pedido de compra origen (moda)',
        index=True,
    )
