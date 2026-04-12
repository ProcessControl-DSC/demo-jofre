# -*- coding: utf-8 -*-
from odoo import api, fields, models


class B2bImportLog(models.Model):
    _name = 'b2b.import.log'
    _description = 'Registro de importación B2B'
    _order = 'date_import desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Referencia',
        readonly=True,
        default='Nuevo',
        copy=False,
    )
    platform = fields.Selection(
        selection=[
            ('joor', 'JOOR'),
            ('nuorder', 'NuORDER'),
            ('mirri', 'MIRRI'),
            ('thenewblack', 'The New Black'),
        ],
        string='Plataforma',
        required=True,
        readonly=True,
    )
    file_name = fields.Char(
        string='Nombre del fichero',
        readonly=True,
    )
    date_import = fields.Datetime(
        string='Fecha de importación',
        default=fields.Datetime.now,
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Importado por',
        default=lambda self: self.env.uid,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('done', 'Completado'),
            ('error', 'Error'),
        ],
        string='Estado',
        default='draft',
        readonly=True,
    )
    purchase_order_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Pedido de compra',
        readonly=True,
    )
    products_created = fields.Integer(
        string='Productos creados',
        readonly=True,
        default=0,
    )
    products_matched = fields.Integer(
        string='Productos encontrados',
        readonly=True,
        default=0,
    )
    lines_imported = fields.Integer(
        string='Líneas importadas',
        readonly=True,
        default=0,
    )
    error_message = fields.Text(
        string='Mensaje de error',
        readonly=True,
    )
    log_line_ids = fields.One2many(
        comodel_name='b2b.import.log.line',
        inverse_name='log_id',
        string='Líneas de detalle',
        readonly=True,
    )
    supplier_name = fields.Char(
        string='Proveedor detectado',
        readonly=True,
    )
    po_number_external = fields.Char(
        string='Nº pedido plataforma',
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'b2b.import.log'
                ) or 'Nuevo'
        return super().create(vals_list)

    def action_view_purchase_order(self):
        """Abrir el pedido de compra asociado."""
        self.ensure_one()
        if self.purchase_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id': self.purchase_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }


class B2bImportLogLine(models.Model):
    _name = 'b2b.import.log.line'
    _description = 'Línea de detalle de importación B2B'
    _order = 'line_number'

    log_id = fields.Many2one(
        comodel_name='b2b.import.log',
        string='Registro de importación',
        required=True,
        ondelete='cascade',
    )
    line_number = fields.Integer(
        string='Nº línea',
    )
    style_number = fields.Char(
        string='Referencia estilo',
    )
    color = fields.Char(
        string='Color',
    )
    size = fields.Char(
        string='Talla',
    )
    quantity = fields.Float(
        string='Cantidad',
    )
    price = fields.Float(
        string='Precio mayorista',
    )
    retail_price = fields.Float(
        string='Precio PVP',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Producto',
    )
    state = fields.Selection(
        selection=[
            ('ok', 'Encontrado'),
            ('created', 'Creado'),
            ('error', 'Error'),
        ],
        string='Estado',
        default='ok',
    )
    message = fields.Char(
        string='Mensaje',
    )
