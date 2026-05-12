{
    "name": "PC POS Re-invoice",
    "version": "19.0.4.1.1",
    "summary": "Refacturar, navegar y enviar por correo facturas de pedidos POS",
    "description": """
Refacturación de pedidos POS pagados:
=====================================

* Refacturar un pedido pagado desde la pantalla de tickets del TPV
  cambiando el cliente.
* Genera la rectificativa de la factura original y emite una nueva
  factura al cliente correcto, manteniendo los apuntes de pago
  reconciliados de forma atómica.
* Envío opcional de la nueva factura por correo electrónico al cliente.
* Botón independiente para reenviar la factura de un pedido por
  correo electrónico desde la pantalla de tickets.
* Smart button en la vista de factura para navegar entre la factura
  original, la rectificativa y la nueva factura sustitutiva.
* Soporte automático de la localización española (factura simplificada
  y Veri*Factu) si los módulos correspondientes están instalados.
    """,
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "license": "LGPL-3",
    "category": "Sales/Point of Sale",
    "depends": [
        "point_of_sale",
        "account",
    ],
    "data": [
        "views/account_move_views.xml",
        "views/pos_config_views.xml",
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pc_pos_reinvoice/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
