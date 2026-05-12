{
    "name": "PC POS Re-invoice — Spain",
    "version": "19.0.1.0.0",
    "summary": "Soporte para factura simplificada española al refacturar pedidos POS",
    "description": """
Glue entre pc_pos_reinvoice y l10n_es_pos.

Cuando un pedido POS con factura simplificada se refactura desde el TPV,
este módulo se asegura de que la nueva factura emitida al cliente correcto
ya no se marque como simplificada y vaya al diario de facturación normal,
no al diario reservado a las simplificadas.

Auto-instalable en cuanto pc_pos_reinvoice y l10n_es_pos coinciden.
    """,
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "license": "LGPL-3",
    "category": "Sales/Point of Sale",
    "depends": [
        "pc_pos_reinvoice",
        "l10n_es_pos",
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": True,
}
