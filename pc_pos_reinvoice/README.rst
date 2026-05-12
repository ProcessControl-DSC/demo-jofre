==================
PC POS Re-invoice
==================

**Autor:** Process Control | https://www.processcontrol.es

Refacturar un pedido POS pagado desde el propio TPV.

Funcionalidades
===============

* Botón "Refacturar" en la pantalla de tickets del POS, visible cuando el
  pedido está pagado y todavía no ha sido refacturado.
* Cambia el cliente del pedido, lanza una rectificativa de la factura
  original y emite una nueva factura al cliente correcto.
* Reasigna los apuntes de pago al nuevo cliente y los reconcilia con la
  nueva factura, sin crear pagos duplicados.
* Bloqueante automático en pedidos con devoluciones asociadas.
* Booleano de configuración para permitir o no la refacturación tras el
  cierre de sesión.

Configuración
=============

En *Punto de Venta > Configuración > Punto de Venta*, abrir el TPV y en la
sección de facturación marcar "Permitir refacturar tras cierre de sesión"
si se quiere habilitar el flujo después de cerrar la sesión.

Uso
===

1. En el TPV, abrir la lista de tickets.
2. Seleccionar un pedido pagado.
3. Pulsar **Refacturar** y elegir el nuevo cliente.
4. El sistema rectifica la factura original y emite una nueva factura.

Datos técnicos
==============

**Modelos extendidos:**

* ``pos.order`` - campos ``re_invoiced``, ``reinvoice_ids`` y
  método ``action_pos_reinvoice``
* ``pos.config`` - campo ``allow_reinvoice_closed_session``

**Hooks de extensión:**

* ``_reinvoice_break_reconciliation``
* ``_reinvoice_reverse_original``
* ``_reinvoice_clear_localization_flags``
* ``_reinvoice_generate_new_invoice(old_move=None)`` — recibe la factura
  original sustituida como argumento, para que extensiones puedan
  referenciarla sin filtrar reinvoice_ids
* ``_reinvoice_reassign_payments``
* ``_reinvoice_post_audit``

Estos hooks permiten que módulos glue (``pc_pos_reinvoice_l10n_es``,
``pc_pos_reinvoice_verifactu``) extiendan el comportamiento sin tocar
el flujo principal.

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_
