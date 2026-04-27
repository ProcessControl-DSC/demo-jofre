===========================================
POS - Ubicación de origen por línea de venta
===========================================

**Autor:** Process Control | https://www.processcontrol.es

Permite al cajero seleccionar, al añadir un producto al ticket de TPV, la
ubicación de stock interna de la que se coge la unidad vendida. La
selección se propaga al ``stock.move.line`` del albarán generado al cerrar
la sesión del TPV, sobrescribiendo la estrategia de remoción por defecto
(FIFO, LIFO, Closest Location, etc.).

Funcionalidades
===============

* Nuevo campo ``location_id`` en ``pos.order.line``.
* Configuración por TPV: ``Seleccionar ubicación de origen por línea``
  en *Punto de venta > Configuración > Punto de venta*.
* Popup de selección de ubicación en el TPV al añadir producto.

  - Si hay stock en **una sola** ubicación candidata, se asigna sin preguntar.
  - Si hay stock en **más de una**, se abre popup con las ubicaciones y el
    stock disponible por ubicación.
  - Si **no hay stock** en ninguna, la línea queda sin ubicación y aplica la
    estrategia de remoción por defecto.
* Visualización de la ubicación elegida en la línea del ticket, con posibilidad
  de cambiarla al hacer clic.
* Propagación al albarán: al cerrar la sesión, los ``stock.move`` generados
  respetan la ubicación de cada línea.

Requisitos
==========

* Odoo 19.
* Módulos estándar ``point_of_sale`` y ``stock``.
* Activar **Ubicaciones de almacenamiento** en *Inventario > Configuración > Ajustes*.

Configuración
=============

1. Ir a *Punto de venta > Configuración > Punto de venta*.
2. Seleccionar el TPV.
3. Activar la opción **Seleccionar ubicación de origen por línea**.

Uso
===

En el TPV, al añadir un producto al ticket:

* Si tiene stock en **varias ubicaciones internas** hijas de la ubicación
  origen del tipo de operación del TPV, se abre un popup para que el cajero
  seleccione.
* En la línea del ticket, la ubicación elegida aparece con un icono de
  marcador. Al clic, se puede cambiar.

Al cerrar la sesión, el albarán generado (``WH/POS/xxxxx``) tiene sus
movimientos de stock con las ubicaciones elegidas, respetándolas sobre la
estrategia de remoción configurada.

Datos técnicos
==============

**Modelos extendidos:**

* ``pos.config`` — campo ``allow_line_location_selection``
* ``pos.order.line`` — campo ``location_id``
* ``pos.session`` — extensión del carga de modelos POS
* ``stock.location`` — añadida herencia ``pos.load.mixin``
* ``stock.quant`` — añadida herencia ``pos.load.mixin``
* ``stock.picking`` — override de ``_create_move_from_pos_order_lines`` y
  ``_prepare_stock_move_vals``

Limitaciones
============

* Solo aplica al flujo POS inmediato. No aplica al flujo de entrega diferida
  vía ``_launch_stock_rule_from_pos_order_lines``.
* Productos con trazabilidad por lote/serie siguen la lógica estándar de
  asignación por lote; la selección de ubicación manual no interfiere con
  la asignación por lote.

Créditos
========

**Desarrollado por** `Process Control <https://www.processcontrol.es>`_
