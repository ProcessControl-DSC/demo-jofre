{
    "name": "PC POS Re-invoice",
    "version": "19.0.1.0.0",
    "summary": "Refacturar un pedido POS pagado cambiando el cliente",
    "description": """
Permite refacturar un pedido POS pagado desde el propio TPV.
Cambia el cliente del pedido, lanza una rectificativa de la factura
original y emite una factura nueva al cliente correcto, manteniendo
los apuntes de pago reconciliados de forma atómica.

Pensado para los casos en que el cliente solicita factura completa
(o cambio de destinatario) cuando ya ha salido del TPV con su ticket
o factura simplificada en mano.
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
