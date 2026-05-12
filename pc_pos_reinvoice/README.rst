====================
PC POS Re-invoice
====================

**Autor:** Process Control | https://www.processcontrol.es

Refacturar y reenviar facturas de pedidos POS desde el propio TPV.

Funcionalidades
===============

**Refacturar pedidos pagados**

* Botón "Refacturar" en la pantalla de tickets del POS, visible cuando el
  pedido está pagado y todavía no ha sido refacturado.
* Cambia el cliente del pedido, lanza una rectificativa de la factura
  original y emite una nueva factura al cliente correcto.
* Reasigna los apuntes de pago al nuevo cliente y los reconcilia con la
  nueva factura, sin crear pagos duplicados.
* Bloqueante automático en pedidos con devoluciones asociadas.
* Soporta los flujos de localización española (factura simplificada y
  Veri*Factu) cuando los módulos correspondientes están instalados.

**Envío de factura por correo**

* Botón "Enviar factura por email" en la pantalla de tickets para
  reenviar la factura de un pedido facturado al correo del cliente.
* Al finalizar una refacturación, opcionalmente solicita el correo del
  nuevo cliente para enviarle la nueva factura.

Configuración
=============

En *Punto de Venta > Configuración > Punto de Venta*, abrir el TPV y en
la sección de facturación encontrarás:

* **Permitir refacturar pedidos** — habilita el botón Refacturar.
* **Permitir refacturar tras cierre de sesión** — permite refacturar
  cuando la sesión POS ya está cerrada.
* **Preguntar por email tras refacturar** — al terminar la refacturación,
  ofrece enviar la nueva factura por correo al nuevo cliente.
* **Permitir enviar factura por email** — habilita el botón de reenvío
  por correo en la pantalla de tickets.

Uso
===

**Refacturar un pedido**

1. En el TPV, abrir la lista de tickets.
2. Seleccionar un pedido pagado.
3. Pulsar **Refacturar** y elegir el nuevo cliente.
4. El sistema rectifica la factura original y emite una nueva factura.
5. Si está activo, ofrece enviar la nueva factura por correo electrónico.

**Reenviar factura por correo**

1. En el TPV, abrir la lista de tickets.
2. Seleccionar un pedido con factura emitida.
3. Pulsar **Enviar factura por email** e introducir el correo destino.

Integración con localización española
=====================================

Si los módulos ``l10n_es_pos`` y/o ``l10n_es_edi_verifactu`` están
instalados, la refacturación adapta automáticamente el flujo:

* **l10n_es_pos** — desmarca ``is_l10n_es_simplified_invoice`` antes de
  emitir la nueva factura, de modo que ésta sea ordinaria y vaya al
  diario normal en vez del de simplificadas.
* **l10n_es_edi_verifactu** — escribe la causa de rectificación
  (``l10n_es_edi_verifactu_refund_reason``) en la rectificativa
  ``out_refund`` con el código:

  * **R5** si la factura original era simplificada.
  * **R1** (Art. 80.1/80.2 LIVA y error de derecho) en el resto.

  Y marca la nueva factura emitida con
  ``l10n_es_edi_verifactu_substituted_entry_id`` apuntando a la factura
  original, para que el envío AEAT reporte el flujo como
  ``correction_substitution`` (método "S - sustitución").

Datos técnicos
==============

**Modelos extendidos:**

* ``pos.order`` — campos ``re_invoiced``, ``reinvoice_ids`` y métodos
  ``action_pos_reinvoice``, ``_get_reinvoice_verifactu_refund_reason``
* ``pos.config`` — campos ``allow_reinvoice``,
  ``allow_reinvoice_closed_session``, ``prompt_email_after_reinvoice``
  y ``allow_send_invoice_email``

**Hooks de extensión:**

* ``_reinvoice_break_reconciliation``
* ``_reinvoice_reverse_original``
* ``_reinvoice_clear_localization_flags``
* ``_reinvoice_generate_new_invoice(old_move=None)`` — recibe la factura
  original sustituida como argumento, para que extensiones puedan
  referenciarla sin filtrar reinvoice_ids
* ``_reinvoice_reassign_payments``
* ``_reinvoice_post_audit``

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_
