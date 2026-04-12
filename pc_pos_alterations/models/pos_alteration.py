# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class PosAlteration(models.Model):
    _name = 'pos.alteration'
    _description = 'Arreglo de Prenda'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_created desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Referencia',
        required=True,
        readonly=True,
        default='/',
        copy=False,
    )
    pos_order_id = fields.Many2one(
        'pos.order',
        string='Pedido TPV',
        ondelete='set null',
        index=True,
    )
    pos_order_line_id = fields.Many2one(
        'pos.order.line',
        string='Línea de prenda (TPV)',
        ondelete='set null',
        help='Línea del pedido TPV que corresponde a la prenda.',
    )
    alteration_line_id = fields.Many2one(
        'pos.order.line',
        string='Línea de arreglo (TPV)',
        ondelete='set null',
        help='Línea del pedido TPV que corresponde al producto de arreglo.',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        index=True,
        tracking=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto (prenda)',
        index=True,
    )
    alteration_type_id = fields.Many2one(
        'alteration.type',
        string='Tipo de arreglo',
        required=True,
        tracking=True,
    )
    description = fields.Text(string='Notas / Descripción del arreglo')
    user_id = fields.Many2one(
        'res.users',
        string='Creado por',
        default=lambda self: self.env.user,
        tracking=True,
    )
    tailor_id = fields.Many2one(
        'res.users',
        string='Costurera / Sastre',
        tracking=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Tienda / Almacén',
        tracking=True,
    )
    date_created = fields.Datetime(
        string='Fecha de creación',
        default=fields.Datetime.now,
        readonly=True,
    )
    date_promised = fields.Date(
        string='Fecha de entrega prometida',
        tracking=True,
    )
    date_done = fields.Datetime(
        string='Fecha de finalización',
        readonly=True,
    )
    date_delivered = fields.Datetime(
        string='Fecha de entrega al cliente',
        readonly=True,
    )
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Curso'),
        ('ready', 'Listo para recoger'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='pending', required=True, tracking=True, index=True)
    delivery_method = fields.Selection([
        ('pickup_store', 'Recogida en tienda'),
        ('ship_customer', 'Envío a domicilio'),
    ], string='Método de entrega', default='pickup_store')
    move_to_workshop_id = fields.Many2one(
        'stock.move',
        string='Movimiento a taller',
        readonly=True,
        copy=False,
    )
    move_to_store_id = fields.Many2one(
        'stock.move',
        string='Movimiento a tienda',
        readonly=True,
        copy=False,
    )
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Evento de calendario',
        readonly=True,
        copy=False,
    )
    cost = fields.Float(
        string='Coste del arreglo',
        digits='Product Price',
        default=0.0,
    )
    charged_to_customer = fields.Boolean(
        string='Cobrado al cliente',
        default=True,
        help='Si está desmarcado, el arreglo se considera cortesía de la tienda.',
    )
    is_overdue = fields.Boolean(
        string='Vencido',
        compute='_compute_is_overdue',
        store=True,
    )

    @api.depends('date_promised', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state in ('pending', 'in_progress') and rec.date_promised:
                rec.is_overdue = rec.date_promised < today
            else:
                rec.is_overdue = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.alteration') or '/'
        return super().create(vals_list)

    # --- Ubicación del taller ---

    def _get_workshop_location(self):
        """Devuelve la ubicación 'Taller de Costura' del almacén asociado."""
        self.ensure_one()
        if not self.warehouse_id:
            raise UserError(_('No se ha definido un almacén/tienda para este arreglo.'))
        workshop = self.env['stock.location'].search([
            ('name', '=', 'Taller de Costura'),
            ('location_id', '=', self.warehouse_id.lot_stock_id.id),
            ('usage', '=', 'internal'),
        ], limit=1)
        if not workshop:
            workshop = self.env['stock.location'].create({
                'name': 'Taller de Costura',
                'usage': 'internal',
                'location_id': self.warehouse_id.lot_stock_id.id,
                'company_id': self.warehouse_id.company_id.id,
            })
        return workshop

    # --- Movimientos de stock ---

    def _create_stock_move(self, src_location, dest_location):
        """Crea y valida un movimiento de stock para la prenda."""
        self.ensure_one()
        if not self.product_id:
            return self.env['stock.move']
        # Solo productos almacenables generan movimiento de stock
        if self.product_id.type != 'consu':
            return self.env['stock.move']
        move = self.env['stock.move'].create({
            'name': _('Arreglo %s', self.name),
            'product_id': self.product_id.id,
            'product_uom_qty': 1.0,
            'product_uom': self.product_id.uom_id.id,
            'location_id': src_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.name,
            'company_id': self.warehouse_id.company_id.id,
        })
        move._action_confirm()
        move.quantity = 1.0
        move.picked = True
        move._action_done()
        return move

    # --- Evento de calendario ---

    def _create_calendar_event(self):
        """Crea un evento de calendario para el sastre/costurera."""
        self.ensure_one()
        partner_name = self.partner_id.name or 'Sin cliente'
        type_name = self.alteration_type_id.name or ''
        summary = _('Arreglo %s - %s - %s', self.name, type_name, partner_name)

        product_info = self.product_id.display_name if self.product_id else ''
        description_parts = [
            _('Referencia: %s', self.name),
            _('Cliente: %s', partner_name),
            _('Producto: %s', product_info),
            _('Tipo: %s', type_name),
        ]
        if self.description:
            description_parts.append(_('Notas: %s', self.description))

        attendee_partner_ids = []
        if self.tailor_id and self.tailor_id.partner_id:
            attendee_partner_ids.append(self.tailor_id.partner_id.id)

        start_dt = self.date_created or fields.Datetime.now()
        if self.date_promised:
            from datetime import datetime, time
            stop_dt = fields.Datetime.to_datetime(
                datetime.combine(self.date_promised, time(18, 0, 0))
            )
        else:
            stop_dt = start_dt + timedelta(days=self.alteration_type_id.default_duration_days or 3)

        event = self.env['calendar.event'].create({
            'name': summary,
            'description': '\n'.join(description_parts),
            'start': start_dt,
            'stop': stop_dt,
            'allday': False,
            'user_id': self.tailor_id.id if self.tailor_id else self.env.user.id,
            'partner_ids': [(6, 0, attendee_partner_ids)] if attendee_partner_ids else False,
        })
        return event

    # --- Acciones de cambio de estado ---

    def action_start(self):
        """Pendiente -> En Curso: mueve la prenda al taller."""
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Solo se pueden iniciar arreglos en estado Pendiente.'))
            workshop = rec._get_workshop_location()
            store_stock = rec.warehouse_id.lot_stock_id
            move = rec._create_stock_move(store_stock, workshop)
            event = rec._create_calendar_event()
            rec.write({
                'state': 'in_progress',
                'move_to_workshop_id': move.id if move else False,
                'calendar_event_id': event.id,
            })

    def action_ready(self):
        """En Curso -> Listo: devuelve la prenda del taller a la tienda."""
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('Solo se pueden marcar como listo arreglos En Curso.'))
            workshop = rec._get_workshop_location()
            store_stock = rec.warehouse_id.lot_stock_id
            move = rec._create_stock_move(workshop, store_stock)
            rec.write({
                'state': 'ready',
                'move_to_store_id': move.id if move else False,
                'date_done': fields.Datetime.now(),
            })

    def action_deliver(self):
        """Listo -> Entregado: el cliente recoge la prenda."""
        for rec in self:
            if rec.state != 'ready':
                raise UserError(_('Solo se pueden entregar arreglos en estado Listo.'))
            rec.write({
                'state': 'delivered',
                'date_delivered': fields.Datetime.now(),
            })

    def action_cancel(self):
        """Cancela el arreglo. Si estaba en curso, revierte el movimiento de stock."""
        for rec in self:
            if rec.state == 'delivered':
                raise UserError(_('No se puede cancelar un arreglo ya entregado.'))
            if rec.state == 'in_progress':
                workshop = rec._get_workshop_location()
                store_stock = rec.warehouse_id.lot_stock_id
                rec._create_stock_move(workshop, store_stock)
            if rec.calendar_event_id:
                rec.calendar_event_id.unlink()
            rec.write({
                'state': 'cancelled',
                'calendar_event_id': False,
            })

    # --- Smart buttons ---

    def action_view_pos_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'view_mode': 'form',
            'res_id': self.pos_order_id.id,
            'target': 'current',
        }

    def action_view_stock_moves(self):
        self.ensure_one()
        move_ids = []
        if self.move_to_workshop_id:
            move_ids.append(self.move_to_workshop_id.id)
        if self.move_to_store_id:
            move_ids.append(self.move_to_store_id.id)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Movimientos de stock'),
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'target': 'current',
        }

    def action_view_calendar_event(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'res_id': self.calendar_event_id.id,
            'target': 'current',
        }

    # --- Métodos RPC llamados desde el POS ---

    @api.model
    def create_from_pos(self, vals):
        """Crea un arreglo desde el TPV y ejecuta la lógica de negocio completa.

        Se invoca tras la confirmación del pago del pedido TPV.

        Args:
            vals (dict): Diccionario con los datos del arreglo.

        Returns:
            dict: Datos del arreglo creado para mostrar en el TPV.
        """
        alteration_type = self.env['alteration.type'].browse(vals.get('alteration_type_id'))
        if not alteration_type.exists():
            raise UserError(_('Tipo de arreglo no válido.'))

        warehouse_id = vals.get('warehouse_id')
        if not warehouse_id:
            config = self.env['pos.config'].browse(vals.get('config_id', 0))
            if config.exists() and config.picking_type_id and config.picking_type_id.warehouse_id:
                warehouse_id = config.picking_type_id.warehouse_id.id

        date_promised = vals.get('date_promised')
        if not date_promised:
            date_promised = fields.Date.context_today(self) + timedelta(
                days=alteration_type.default_duration_days or 3
            )

        alteration = self.create({
            'pos_order_id': vals.get('pos_order_id'),
            'pos_order_line_id': vals.get('pos_order_line_id'),
            'alteration_line_id': vals.get('alteration_line_id'),
            'partner_id': vals.get('partner_id'),
            'product_id': vals.get('product_id'),
            'alteration_type_id': alteration_type.id,
            'description': vals.get('description', ''),
            'user_id': vals.get('user_id') or self.env.user.id,
            'tailor_id': vals.get('tailor_id'),
            'warehouse_id': warehouse_id,
            'date_promised': date_promised,
            'cost': vals.get('cost', alteration_type.product_id.list_price if alteration_type.product_id else 0),
            'delivery_method': vals.get('delivery_method', 'pickup_store'),
        })

        # Iniciar automáticamente: mover prenda al taller
        alteration.action_start()

        return {
            'id': alteration.id,
            'name': alteration.name,
            'state': alteration.state,
            'partner_name': alteration.partner_id.name or '',
            'partner_phone': alteration.partner_id.phone or alteration.partner_id.mobile or '',
            'product_name': alteration.product_id.display_name if alteration.product_id else '',
            'alteration_type': alteration.alteration_type_id.name,
            'description': alteration.description or '',
            'date_promised': str(alteration.date_promised) if alteration.date_promised else '',
            'delivery_method': alteration.delivery_method,
            'cost': alteration.cost,
            'warehouse_name': alteration.warehouse_id.name if alteration.warehouse_id else '',
        }

    @api.model
    def get_alterations_for_pos(self, warehouse_id, states=None):
        """Obtiene los arreglos de una tienda para mostrar en el TPV."""
        domain = [('warehouse_id', '=', warehouse_id)]
        if states:
            domain.append(('state', 'in', states))
        else:
            domain.append(('state', '!=', 'cancelled'))

        alterations = self.search(domain, order='date_promised asc, id desc')
        result = []
        for alt in alterations:
            result.append({
                'id': alt.id,
                'name': alt.name,
                'state': alt.state,
                'partner_name': alt.partner_id.name or '',
                'partner_phone': alt.partner_id.phone or alt.partner_id.mobile or '',
                'product_name': alt.product_id.display_name if alt.product_id else '',
                'alteration_type': alt.alteration_type_id.name,
                'alteration_type_code': alt.alteration_type_id.code,
                'description': alt.description or '',
                'date_created': str(alt.date_created) if alt.date_created else '',
                'date_promised': str(alt.date_promised) if alt.date_promised else '',
                'date_done': str(alt.date_done) if alt.date_done else '',
                'date_delivered': str(alt.date_delivered) if alt.date_delivered else '',
                'delivery_method': alt.delivery_method,
                'cost': alt.cost,
                'is_overdue': alt.is_overdue,
                'tailor_name': alt.tailor_id.name if alt.tailor_id else '',
            })
        return result

    @api.model
    def change_state_from_pos(self, alteration_id, new_state):
        """Cambia el estado de un arreglo desde el TPV."""
        alteration = self.browse(alteration_id)
        if not alteration.exists():
            raise UserError(_('Arreglo no encontrado.'))

        if new_state == 'in_progress':
            alteration.action_start()
        elif new_state == 'ready':
            alteration.action_ready()
        elif new_state == 'delivered':
            alteration.action_deliver()
        elif new_state == 'cancelled':
            alteration.action_cancel()
        else:
            raise UserError(_('Estado no válido: %s', new_state))

        return {
            'id': alteration.id,
            'name': alteration.name,
            'state': alteration.state,
        }

    @api.model
    def search_alterations_from_pos(self, warehouse_id, search_term):
        """Busca arreglos por nombre de cliente o referencia de arreglo."""
        domain = [
            ('warehouse_id', '=', warehouse_id),
            ('state', '!=', 'cancelled'),
            '|',
            ('name', 'ilike', search_term),
            ('partner_id.name', 'ilike', search_term),
        ]
        alterations = self.search(domain, order='date_promised asc, id desc')
        result = []
        for alt in alterations:
            result.append({
                'id': alt.id,
                'name': alt.name,
                'state': alt.state,
                'partner_name': alt.partner_id.name or '',
                'partner_phone': alt.partner_id.phone or alt.partner_id.mobile or '',
                'product_name': alt.product_id.display_name if alt.product_id else '',
                'alteration_type': alt.alteration_type_id.name,
                'description': alt.description or '',
                'date_promised': str(alt.date_promised) if alt.date_promised else '',
                'delivery_method': alt.delivery_method,
                'cost': alt.cost,
                'is_overdue': alt.is_overdue,
            })
        return result
