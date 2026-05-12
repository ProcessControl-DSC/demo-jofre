==========================
PC POS Re-invoice — Spain
==========================

**Autor:** Process Control | https://www.processcontrol.es

Glue entre ``pc_pos_reinvoice`` y ``l10n_es_pos``.

Cuando un pedido POS con factura simplificada se refactura desde el TPV,
este módulo se asegura de que la nueva factura emitida al cliente correcto
ya no se marque como simplificada y vaya al diario de facturación normal,
no al diario reservado a las simplificadas.

Es auto-instalable cuando ``pc_pos_reinvoice`` y ``l10n_es_pos`` están ambos
presentes.

Datos técnicos
==============

**Hooks extendidos:**

* ``pos.order._reinvoice_clear_localization_flags`` -
  resetea ``is_l10n_es_simplified_invoice`` antes de regenerar la nueva
  factura, de modo que el override de ``l10n_es_pos`` en
  ``_prepare_invoice_vals`` no fuerce el diario de simplificadas.

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_
