from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_reinvoice_closed_session = fields.Boolean(
        string="Permitir refacturar tras cierre de sesión",
        default=False,
        help="Si está activo, los pedidos pueden refacturarse incluso "
             "cuando la sesión POS ya está cerrada. Por defecto desactivado "
             "para forzar el control contable a través de la sesión abierta.",
    )
