{
    "name": "PC POS Re-invoice — Veri*Factu",
    "version": "19.0.1.0.0",
    "summary": "Marca rectificativa y sustitución Veri*Factu al refacturar pedidos POS",
    "description": """
Glue entre pc_pos_reinvoice y l10n_es_edi_verifactu.

Cuando un pedido POS se refactura desde el TPV bajo el régimen Veri*Factu,
este módulo se asegura de que:

* La rectificativa generada lleva la causa apropiada (R5 si la factura
  original era simplificada, R1 — error de derecho — en el resto de casos).
* La nueva factura emitida queda referenciada como sustitución de la
  rectificada vía ``l10n_es_edi_verifactu_substituted_entry_id``,
  permitiendo que Veri*Factu reporte ``reversal_for_substitution`` y
  Hacienda trace el flujo correctamente.

Auto-instalable cuando pc_pos_reinvoice y l10n_es_edi_verifactu coinciden.
    """,
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "license": "LGPL-3",
    "category": "Sales/Point of Sale",
    "depends": [
        "pc_pos_reinvoice",
        "l10n_es_edi_verifactu",
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": True,
}
