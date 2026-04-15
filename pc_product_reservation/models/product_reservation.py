# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class ProductReservation(models.Model):
    _name = 'product.reservation'
    _description = 'Reserva de producto para cliente'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'pos.load.mixin']
    _order = 'date_reservation desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo'),
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
        check_company=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        tracking=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Tienda / Almacén',
        required=True,
        check_company=True,
        default=lambda self: self.env.user._get_default_warehouse_id(),
        tracking=True,
    )
    config_id = fields.Many2one(
        'pos.config',
        string='Punto de Venta',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        'product.reservation.line',
        'reservation_id',
        string='Líneas de reserva',
        copy=True,
    )
    date_reservation = fields.Datetime(
        string='Fecha de reserva',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    date_expiry = fields.Datetime(
        string='Fecha de expiración',
        compute='_compute_date_expiry',
        store=True,
        readonly=False,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmada'),
            ('done', 'Cobrada'),
            ('cancelled', 'Cancelada'),
            ('expired', 'Expirada'),
        ],
        string='Estado',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    note = fields.Text(
        string='Notas',
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Pedido de venta',
        copy=False,
        readonly=True,
    )
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Pedido de TPV',
        copy=False,
        readonly=True,
    )
    reservation_location_id = fields.Many2one(
        'stock.location',
        string='Ubicación de reservas',
        compute='_compute_reservation_location_id',
    )
    line_count = fields.Integer(
        string='Nº artículos',
        compute='_compute_line_count',
    )
    move_count = fields.Integer(
        string='Nº movimientos',
        compute='_compute_move_count',
    )
    is_expired = fields.Boolean(
        string='Expirada',
        compute='_compute_is_expired',
        search='_search_is_expired',
    )

    # -------------------------------------------------------------------------
    # POS LOAD MIXIN
    # -------------------------------------------------------------------------

    @api.model
    def _load_pos_data_domain(self, data, config):
        # Load confirmed reservations for the warehouse of this POS config
        warehouse = config.picking_type_id.warehouse_id
        return [
            ('state', '=', 'confirmed'),
            ('warehouse_id', '=', warehouse.id),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            'id', 'name', 'partner_id', 'user_id', 'warehouse_id',
            'config_id', 'date_reservation', 'date_expiry', 'state',
            'note', 'sale_order_id', 'pos_order_id', 'write_date',
        ]

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------

    @api.depends('date_reservation')
    def _compute_date_expiry(self):
        default_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'pc_product_reservation.default_reservation_days', default='7',
        ))
        for rec in self:
            if rec.date_reservation and not rec.date_expiry:
                rec.date_expiry = rec.date_reservation + relativedelta(days=default_days)

    @api.depends('warehouse_id')
    def _compute_reservation_location_id(self):
        location_name = 'Reservas Clientes'
        for rec in self:
            if rec.warehouse_id:
                rec.reservation_location_id = self.env['stock.location'].sudo().search([
                    ('name', '=', location_name),
                    ('location_id', '=', rec.warehouse_id.lot_stock_id.id),
                    ('usage', '=', 'internal'),
                ], limit=1)
            else:
                rec.reservation_location_id = False

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.move_id')
    def _compute_move_count(self):
        for rec in self:
            rec.move_count = len(rec.line_ids.move_id)

    @api.depends('date_expiry', 'state')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_expired = (
                rec.state == 'confirmed'
                and rec.date_expiry
                and rec.date_expiry < now
            )

    def _search_is_expired(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_('Operador no soportado para campo expirado.'))
        now = fields.Datetime.now()
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [
                ('state', '=', 'confirmed'),
                ('date_expiry', '<', now),
            ]
        return [
            '|',
            ('state', '!=', 'confirmed'),
            ('date_expiry', '>=', now),
        ]

    # -------------------------------------------------------------------------
    # CRUD / ORM
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'product.reservation',
                ) or _('Nuevo')
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # CONSTRAINT
    # -------------------------------------------------------------------------

    @api.constrains('line_ids')
    def _check_lines(self):
        for rec in self:
            if rec.state == 'confirmed' and not rec.line_ids:
                raise ValidationError(
                    _('No se puede confirmar una reserva sin líneas de producto.')
                )

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_confirm(self):
        """Confirm reservation: move stock to reservation location."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(
                    _('Solo se pueden confirmar reservas en estado borrador.')
                )
            if not rec.line_ids:
                raise UserError(
                    _('No se puede confirmar una reserva sin líneas de producto.')
                )
            if not rec.reservation_location_id:
                raise UserError(
                    _(
                        'No se ha encontrado la ubicación "Reservas Clientes" para '
                        'el almacén "%(warehouse)s". Verifique la configuración del módulo.',
                        warehouse=rec.warehouse_id.name,
                    )
                )
            rec._create_reservation_moves()
            rec.state = 'confirmed'

    def action_cancel(self):
        """Cancel reservation: return stock to main location."""
        for rec in self:
            if rec.state not in ('draft', 'confirmed'):
                raise UserError(
                    _('Solo se pueden cancelar reservas en estado borrador o confirmado.')
                )
            if rec.state == 'confirmed':
                rec._create_return_moves()
            rec.state = 'cancelled'

    def action_done(self):
        """Mark reservation as done (paid via POS)."""
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(
                    _('Solo se pueden cobrar reservas confirmadas.')
                )
            rec._create_return_moves()
            rec.state = 'done'

    def action_convert_to_sale(self):
        """Convert reservation to a sale order."""
        self.ensure_one()
        if self.state != 'confirmed':
            raise UserError(
                _('Solo se pueden convertir a venta reservas confirmadas.')
            )
        sale_order = self._create_sale_order()
        self.sale_order_id = sale_order.id
        self._create_return_moves()
        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedido de venta'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_set_draft(self):
        """Reset to draft from cancelled/expired."""
        for rec in self:
            if rec.state not in ('cancelled', 'expired'):
                raise UserError(
                    _('Solo se pueden volver a borrador reservas canceladas o expiradas.')
                )
            rec.state = 'draft'

    def action_view_sale_order(self):
        """Open linked sale order."""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('Esta reserva no tiene un pedido de venta vinculado.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedido de venta'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_stock_moves(self):
        """Open linked stock moves."""
        self.ensure_one()
        move_ids = self.line_ids.move_id.ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Movimientos de stock'),
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # POS RPC METHODS
    # -------------------------------------------------------------------------

    @api.model
    def create_from_pos(self, vals):
        """Create a reservation from the POS interface.

        :param vals: dict with keys:
            - partner_id: int
            - config_id: int
            - note: str (optional)
            - lines: list of dicts with keys:
                - product_id: int
                - product_qty: float
                - price_unit: float
        :return: dict with reservation data
        """
        config = self.env['pos.config'].browse(vals['config_id'])
        warehouse = config.picking_type_id.warehouse_id

        default_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'pc_product_reservation.default_reservation_days', default='7',
        ))
        now = fields.Datetime.now()

        reservation = self.create({
            'partner_id': vals['partner_id'],
            'user_id': self.env.user.id,
            'warehouse_id': warehouse.id,
            'config_id': config.id,
            'date_reservation': now,
            'date_expiry': now + relativedelta(days=default_days),
            'note': vals.get('note', ''),
            'line_ids': [
                (0, 0, {
                    'product_id': line['product_id'],
                    'product_qty': line['product_qty'],
                    'price_unit': line['price_unit'],
                })
                for line in vals.get('lines', [])
            ],
        })
        reservation.action_confirm()

        return {
            'id': reservation.id,
            'name': reservation.name,
            'partner_id': reservation.partner_id.id,
            'partner_name': reservation.partner_id.name,
            'date_reservation': fields.Datetime.to_string(reservation.date_reservation),
            'date_expiry': fields.Datetime.to_string(reservation.date_expiry),
            'state': reservation.state,
            'lines': [
                {
                    'id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.display_name,
                    'product_qty': line.product_qty,
                    'price_unit': line.price_unit,
                }
                for line in reservation.line_ids
            ],
        }

    @api.model
    def get_reservations_for_pos(self, config_id):
        """Get active reservations for a POS config's warehouse.

        :param config_id: int
        :return: list of dicts with reservation data
        """
        config = self.env['pos.config'].browse(config_id)
        warehouse = config.picking_type_id.warehouse_id

        reservations = self.search([
            ('state', '=', 'confirmed'),
            ('warehouse_id', '=', warehouse.id),
        ], order='date_reservation desc')

        result = []
        for res in reservations:
            result.append({
                'id': res.id,
                'name': res.name,
                'partner_id': res.partner_id.id,
                'partner_name': res.partner_id.name,
                'date_reservation': fields.Datetime.to_string(res.date_reservation),
                'date_expiry': fields.Datetime.to_string(res.date_expiry),
                'state': res.state,
                'note': res.note or '',
                'lines': [
                    {
                        'id': line.id,
                        'product_id': line.product_id.id,
                        'product_name': line.product_id.display_name,
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                    }
                    for line in res.line_ids
                ],
            })
        return result

    @api.model
    def cancel_from_pos(self, reservation_id):
        """Cancel a reservation from POS.

        :param reservation_id: int
        :return: dict with status
        """
        reservation = self.browse(reservation_id)
        if not reservation.exists():
            return {'success': False, 'message': 'Reserva no encontrada.'}
        try:
            reservation.action_cancel()
            return {'success': True, 'message': 'Reserva cancelada correctamente.'}
        except (UserError, ValidationError) as e:
            return {'success': False, 'message': str(e)}

    @api.model
    def mark_done_from_pos(self, reservation_id, pos_order_id=False):
        """Mark reservation as done (paid) from POS.

        :param reservation_id: int
        :param pos_order_id: int (optional)
        :return: dict with status
        """
        reservation = self.browse(reservation_id)
        if not reservation.exists():
            return {'success': False, 'message': 'Reserva no encontrada.'}
        try:
            reservation.action_done()
            if pos_order_id:
                reservation.pos_order_id = pos_order_id
            return {'success': True, 'message': 'Reserva cobrada correctamente.'}
        except (UserError, ValidationError) as e:
            return {'success': False, 'message': str(e)}

    # -------------------------------------------------------------------------
    # STOCK MOVE HELPERS
    # -------------------------------------------------------------------------

    def _create_reservation_moves(self):
        """Create stock moves: Stock -> Reservation location."""
        self.ensure_one()
        stock_location = self.warehouse_id.lot_stock_id
        reservation_location = self.reservation_location_id

        for line in self.line_ids:
            move_vals = {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': reservation_location.id,
                'origin': self.name,
                'company_id': self.company_id.id,
            }
            move = self.env['stock.move'].sudo().create(move_vals)
            move._action_confirm()
            move.quantity = line.product_qty
            move.picked = True
            move._action_done()
            line.move_id = move.id

    def _create_return_moves(self):
        """Create reverse stock moves: Reservation location -> Stock."""
        self.ensure_one()
        stock_location = self.warehouse_id.lot_stock_id
        reservation_location = self.reservation_location_id

        for line in self.line_ids.filtered(lambda l: l.move_id):
            move_vals = {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': reservation_location.id,
                'location_dest_id': stock_location.id,
                'origin': self.name,
                'company_id': self.company_id.id,
            }
            return_move = self.env['stock.move'].sudo().create(move_vals)
            return_move._action_confirm()
            return_move.quantity = line.product_qty
            return_move.picked = True
            return_move._action_done()

    # -------------------------------------------------------------------------
    # SALE ORDER CREATION
    # -------------------------------------------------------------------------

    def _create_sale_order(self):
        """Create a sale order from the reservation."""
        self.ensure_one()
        so_vals = {
            'partner_id': self.partner_id.id,
            'warehouse_id': self.warehouse_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
            'note': self.note or '',
            'order_line': [
                fields.Command.create({
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'price_unit': line.price_unit,
                })
                for line in self.line_ids
            ],
        }
        return self.env['sale.order'].sudo().create(so_vals)

    # -------------------------------------------------------------------------
    # CRON
    # -------------------------------------------------------------------------

    @api.model
    def _cron_expire_reservations(self):
        """Auto-expire reservations past their expiry date."""
        now = fields.Datetime.now()
        expired_reservations = self.search([
            ('state', '=', 'confirmed'),
            ('date_expiry', '<', now),
        ])

        for reservation in expired_reservations:
            try:
                reservation._create_return_moves()
                reservation.state = 'expired'
                if reservation.user_id:
                    reservation.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=reservation.user_id.id,
                        note=_(
                            'La reserva %(name)s para el cliente %(partner)s ha expirado '
                            'automáticamente. El stock ha sido devuelto al almacén.',
                            name=reservation.name,
                            partner=reservation.partner_id.name,
                        ),
                        summary=_('Reserva expirada: %(name)s', name=reservation.name),
                    )
            except Exception:
                reservation.message_post(
                    body=_(
                        'Error al intentar expirar automáticamente esta reserva. '
                        'Se requiere intervención manual.'
                    ),
                )
