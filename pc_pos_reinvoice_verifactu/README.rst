==============================
PC POS Re-invoice — Veri*Factu
==============================

**Autor:** Process Control | https://www.processcontrol.es

Glue entre ``pc_pos_reinvoice`` y ``l10n_es_edi_verifactu``.

Cuando un pedido POS se refactura desde el TPV bajo el régimen Veri*Factu,
este módulo asegura la coherencia con el reporting a la AEAT en dos puntos:

* **Rectificativa (out_refund)** — recibe el campo
  ``l10n_es_edi_verifactu_refund_reason`` con el código:

  * **R5** si la factura original era simplificada.
  * **R1** (Art. 80.1/80.2 LIVA y error de derecho) en el resto.

* **Nueva factura sustituta (out_invoice)** — recibe el campo
  ``l10n_es_edi_verifactu_substituted_entry_id`` apuntando a la factura
  original. Esto hace que el envío AEAT reporte el flujo como
  ``correction_substitution`` (método "S - sustitución").

El flujo nativo de ``l10n_es_edi_verifactu`` asigna estos campos vía
``account.move.reversal._modify_default_reverse_values``, pero ese método
solo se ejecuta cuando se invoca ``modify_moves()`` (``is_modify=True``).
La refacturación POS de ``pc_pos_reinvoice`` separa rectificativa y nueva
factura, llamando ``refund_moves()``, así que este glue asigna los campos
a mano para mantener el mismo reporting AEAT.

Es auto-instalable cuando ``pc_pos_reinvoice`` y ``l10n_es_edi_verifactu``
están ambos presentes.

Datos técnicos
==============

**Hooks extendidos:**

* ``pos.order._reinvoice_reverse_original`` — escribe
  ``l10n_es_edi_verifactu_refund_reason`` en las líneas ``out_refund``
  generadas (rectificativa).
* ``pos.order._reinvoice_generate_new_invoice`` — escribe
  ``l10n_es_edi_verifactu_substituted_entry_id`` en la nueva factura
  emitida, apuntando a la factura original.

**Helpers:**

* ``pos.order._get_reinvoice_verifactu_refund_reason`` — devuelve el
  código R1/R5 según si la factura original era simplificada.

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_
