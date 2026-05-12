==============================
PC POS Re-invoice — Veri*Factu
==============================

**Autor:** Process Control | https://www.processcontrol.es

Glue entre ``pc_pos_reinvoice`` y ``l10n_es_edi_verifactu``.

Cuando un pedido POS se refactura desde el TPV bajo el régimen Veri*Factu,
este módulo asegura la coherencia con el reporting a la AEAT asignando la
causa de rectificación a la rectificativa generada:

* **R5** — factura rectificativa concerniente a una factura simplificada.
* **R1** — Art. 80.1/80.2 LIVA y error de derecho (caso por defecto al
  cambiar el destinatario de una factura ordinaria ya emitida).

El campo ``l10n_es_edi_verifactu_substituted_entry_id`` (FacturaSustituida
del esquema AEAT) lo coloca automáticamente el wizard
``account.move.reversal`` del módulo ``l10n_es_edi_verifactu`` apuntando
desde la rectificativa a la factura original. No es necesario que este
glue lo gestione: el reporting ``correction_substitution`` (método
"S - sustitución" AEAT) se construye así correctamente.

Es auto-instalable cuando ``pc_pos_reinvoice`` y ``l10n_es_edi_verifactu``
están ambos presentes.

Datos técnicos
==============

**Hooks extendidos:**

* ``pos.order._reinvoice_reverse_original`` — tras ejecutar la rectificativa
  estándar del wizard, escribe ``l10n_es_edi_verifactu_refund_reason`` en
  las líneas ``out_refund`` generadas.

**Helpers:**

* ``pos.order._get_reinvoice_verifactu_refund_reason`` — devuelve el
  código R1/R5 según si la factura original era simplificada.

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_
