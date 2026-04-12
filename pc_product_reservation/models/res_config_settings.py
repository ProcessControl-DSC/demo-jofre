# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pc_reservation_default_days = fields.Integer(
        string='Duración de reserva por defecto (días)',
        config_parameter='pc_product_reservation.default_reservation_days',
        default=7,
        help='Número de días que una reserva estará activa antes de expirar automáticamente.',
    )
    pc_reservation_auto_expire = fields.Boolean(
        string='Expirar reservas automáticamente',
        config_parameter='pc_product_reservation.auto_expire_reservations',
        default=True,
        help='Si está activado, las reservas confirmadas que superen la fecha de expiración '
             'se cancelarán automáticamente y el stock volverá al almacén.',
    )
