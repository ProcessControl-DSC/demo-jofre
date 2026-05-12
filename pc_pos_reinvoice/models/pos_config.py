from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    allow_reinvoice = fields.Boolean(
        string="Permitir refacturar pedidos",
        default=True,
        help="Habilita el botón 'Refacturar' en la pantalla de tickets "
             "del TPV. Permite cambiar el cliente de un pedido pagado, "
             "rectificar la factura original y emitir una nueva al cliente "
             "correcto.",
    )
    allow_reinvoice_closed_session = fields.Boolean(
        string="Permitir refacturar tras cierre de sesión",
        default=False,
        help="Si está activo, los pedidos pueden refacturarse incluso "
             "cuando la sesión POS ya está cerrada. Por defecto desactivado "
             "para forzar el control contable a través de la sesión abierta.",
    )
    prompt_email_after_reinvoice = fields.Boolean(
        string="Preguntar por email tras refacturar",
        default=True,
        help="Al terminar la refacturación, ofrecer el envío de la nueva "
             "factura por correo electrónico al nuevo cliente.",
    )
    allow_send_invoice_email = fields.Boolean(
        string="Permitir enviar factura por email",
        default=True,
        help="Añade un botón 'Enviar factura por email' en la pantalla "
             "de tickets para reenviar la factura de cualquier pedido "
             "facturado al correo del cliente.",
    )

    _PC_REINVOICE_POS_FIELDS = (
        "allow_reinvoice",
        "allow_reinvoice_closed_session",
        "prompt_email_after_reinvoice",
        "allow_send_invoice_email",
    )

    @api.model
    def _load_pos_data_read(self, records, config):
        """Expone los campos del módulo al frontend del POS sin restringir
        la lista de fields que carga el core.

        El patrón ``_load_pos_data_fields = super() + [...]`` no funciona
        para ``pos.config`` en v19: el mixin base devuelve ``[]`` y el core
        de ``point_of_sale`` no sobrescribe ``_load_pos_data_fields``,
        confiando en que ``records.read([])`` devuelva todos los campos.
        Si añadimos elementos a esa lista, ``read()`` se restringe a esos
        y rompe el ``_load_pos_data_read`` del core (``KeyError:
        'use_pricelist'``)."""
        read_records = super()._load_pos_data_read(records, config)
        if not read_records:
            return read_records
        for record in read_records:
            cfg = self.browse(record["id"])
            for fname in self._PC_REINVOICE_POS_FIELDS:
                record[fname] = bool(cfg[fname])
        return read_records
