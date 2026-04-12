# -*- coding: utf-8 -*-
import base64
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from ..parsers.joor_parser import parse_joor_file
from ..parsers.nuorder_parser import parse_nuorder_file
from ..parsers.mirri_parser import parse_mirri_file

_logger = logging.getLogger(__name__)


class B2bOrderImportWizard(models.TransientModel):
    _name = 'b2b.order.import.wizard'
    _description = 'Asistente de importación de pedidos B2B'

    # =========================================================================
    # Campos — Paso 1: Selección de plataforma
    # =========================================================================
    platform = fields.Selection(
        selection=[
            ('joor', 'JOOR'),
            ('nuorder', 'NuORDER'),
            ('mirri', 'MIRRI'),
            ('thenewblack', 'The New Black'),
        ],
        string='Plataforma',
        required=True,
        default='joor',
    )

    # =========================================================================
    # Campos — Paso 2: Subida de fichero
    # =========================================================================
    file_data = fields.Binary(
        string='Fichero',
        attachment=False,
    )
    file_name = fields.Char(
        string='Nombre del fichero',
    )

    # =========================================================================
    # Campos — Paso 3: Previsualización
    # =========================================================================
    preview_line_ids = fields.One2many(
        comodel_name='b2b.order.import.wizard.line',
        inverse_name='wizard_id',
        string='Líneas previsualizadas',
    )
    preview_info = fields.Html(
        string='Información del fichero',
        readonly=True,
    )
    parsed_data_json = fields.Text(
        string='Datos parseados (JSON)',
        readonly=True,
    )

    # =========================================================================
    # Campos — Paso 4: Opciones de configuración
    # =========================================================================
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True,
    )
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Almacén',
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        ),
    )
    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Proveedor',
        domain="[('supplier_rank', '>', 0)]",
    )
    auto_create_products = fields.Boolean(
        string='Crear productos automáticamente',
        default=True,
        help='Si está marcado, los productos que no existan en Odoo se crearán automáticamente.',
    )
    season = fields.Char(
        string='Temporada',
        help='Temporada de moda (ej. 26W, SS26, FW26)',
    )
    detected_brand = fields.Char(
        string='Marca detectada',
        readonly=True,
    )
    detected_po_number = fields.Char(
        string='Nº pedido plataforma',
        readonly=True,
    )

    # =========================================================================
    # Campos — Control de pasos
    # =========================================================================
    state = fields.Selection(
        selection=[
            ('upload', 'Subir fichero'),
            ('preview', 'Previsualización'),
            ('configure', 'Configuración'),
            ('done', 'Completado'),
        ],
        string='Paso',
        default='upload',
    )
    import_log_id = fields.Many2one(
        comodel_name='b2b.import.log',
        string='Registro de importación',
        readonly=True,
    )

    # =========================================================================
    # Acciones de navegación
    # =========================================================================
    def action_parse_file(self):
        """Paso 2 → 3: Parsear el fichero y mostrar previsualización."""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Debe seleccionar un fichero para importar."))

        file_content = base64.b64decode(self.file_data)

        try:
            if self.platform == 'joor':
                parsed = parse_joor_file(file_content)
                self._populate_preview_joor(parsed)
            elif self.platform == 'nuorder':
                parsed = parse_nuorder_file(file_content)
                self._populate_preview_nuorder(parsed)
            elif self.platform == 'mirri':
                parsed = parse_mirri_file(file_content)
                self._populate_preview_mirri(parsed)
            elif self.platform == 'thenewblack':
                # The New Black usa el mismo formato que JOOR
                parsed = parse_joor_file(file_content)
                self._populate_preview_joor(parsed)
            else:
                raise UserError(_("Plataforma no soportada: %s") % self.platform)
        except Exception as e:
            _logger.exception("Error parseando fichero %s", self.file_name)
            raise UserError(
                _("Error al leer el fichero '%s':\n%s") % (self.file_name, str(e))
            ) from e

        # Serializar datos parseados para el paso de confirmación
        import json
        self.parsed_data_json = json.dumps(parsed, default=str)
        self.state = 'preview'

        return self._reopen_wizard()

    def action_configure(self):
        """Paso 3 → 4: Ir a configuración."""
        self.ensure_one()
        self.state = 'configure'

        # Intentar auto-detectar proveedor
        if self.detected_brand and not self.supplier_id:
            supplier = self._find_supplier_by_name(self.detected_brand)
            if supplier:
                self.supplier_id = supplier.id

        return self._reopen_wizard()

    def action_back_to_upload(self):
        """Volver al paso de subida."""
        self.ensure_one()
        self.state = 'upload'
        self.preview_line_ids.unlink()
        self.preview_info = False
        self.parsed_data_json = False
        return self._reopen_wizard()

    def action_back_to_preview(self):
        """Volver al paso de previsualización."""
        self.ensure_one()
        self.state = 'preview'
        return self._reopen_wizard()

    def action_confirm_import(self):
        """Paso 4 → Confirmación: Crear productos y pedido de compra."""
        self.ensure_one()
        import json

        if not self.parsed_data_json:
            raise UserError(_("No hay datos parseados. Vuelva al paso anterior."))

        parsed = json.loads(self.parsed_data_json)

        # Crear registro de log
        log = self.env['b2b.import.log'].create({
            'platform': self.platform,
            'file_name': self.file_name,
            'supplier_name': self.detected_brand or '',
            'po_number_external': self.detected_po_number or '',
        })

        try:
            if self.platform in ('joor', 'thenewblack'):
                self._import_joor(parsed, log)
            elif self.platform == 'nuorder':
                self._import_nuorder(parsed, log)
            elif self.platform == 'mirri':
                self._import_mirri(parsed, log)

            log.write({'state': 'done'})
        except Exception as e:
            _logger.exception("Error en importación B2B")
            log.write({
                'state': 'error',
                'error_message': str(e),
            })
            raise UserError(
                _("Error durante la importación:\n%s") % str(e)
            ) from e

        self.import_log_id = log.id
        self.state = 'done'

        return self._reopen_wizard()

    def action_view_log(self):
        """Abrir el registro de importación."""
        self.ensure_one()
        if self.import_log_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'b2b.import.log',
                'res_id': self.import_log_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_view_purchase_order(self):
        """Abrir el pedido de compra creado."""
        self.ensure_one()
        if self.import_log_id and self.import_log_id.purchase_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id': self.import_log_id.purchase_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

    # =========================================================================
    # Previsualización — JOOR
    # =========================================================================
    def _populate_preview_joor(self, parsed):
        """Rellena las líneas de previsualización para un fichero JOOR."""
        self.preview_line_ids.unlink()

        self.detected_brand = parsed.get('brand', '')
        self.detected_po_number = parsed.get('po_number', '')
        self.season = ''  # JOOR no incluye temporada explícita

        lines = parsed.get('lines', [])
        line_vals = []
        for line in lines:
            line_vals.append({
                'wizard_id': self.id,
                'line_number': line['line_number'],
                'style_number': line['style_number'],
                'style_name': line.get('style_name', ''),
                'color': line.get('color', ''),
                'color_code': line.get('color_code', ''),
                'size': line.get('size', ''),
                'quantity': line.get('quantity', 0),
                'wholesale_price': line.get('wholesale_price', 0),
                'retail_price': line.get('retail_price', 0),
            })

        self.env['b2b.order.import.wizard.line'].create(line_vals)

        # Información de cabecera
        totals = parsed.get('totals', {})
        info_html = (
            '<div style="padding: 10px;">'
            '<table class="table table-sm table-bordered" '
            'style="max-width: 600px;">'
            '<tr><th>Marca</th><td>{brand}</td></tr>'
            '<tr><th>Nº Pedido</th><td>{po}</td></tr>'
            '<tr><th>Estado</th><td>{status}</td></tr>'
            '<tr><th>Fecha creación</th><td>{date}</td></tr>'
            '<tr><th>Inicio envío</th><td>{start}</td></tr>'
            '<tr><th>Fin envío</th><td>{end}</td></tr>'
            '<tr><th>Condiciones pago</th><td>{terms}</td></tr>'
            '<tr><th>Total líneas</th><td>{lines}</td></tr>'
            '<tr><th>Total unidades</th><td>{units}</td></tr>'
            '<tr><th>Subtotal</th><td>{subtotal:.2f} EUR</td></tr>'
            '</table></div>'
        ).format(
            brand=parsed.get('brand', '-'),
            po=parsed.get('po_number', '-'),
            status=parsed.get('status', '-'),
            date=parsed.get('created_date', '-'),
            start=parsed.get('start_ship', '-'),
            end=parsed.get('complete_ship', '-'),
            terms=parsed.get('payment_terms', '-'),
            lines=len(lines),
            units=sum(l['quantity'] for l in lines),
            subtotal=totals.get('subtotal', 0) or sum(
                l['quantity'] * l['wholesale_price'] for l in lines
            ),
        )
        self.preview_info = info_html

    # =========================================================================
    # Previsualización — NuORDER
    # =========================================================================
    def _populate_preview_nuorder(self, parsed):
        """Rellena las líneas de previsualización para un fichero NuORDER."""
        self.preview_line_ids.unlink()

        self.detected_brand = ''  # NuORDER no tiene marca en cabecera
        self.detected_po_number = ''
        self.season = parsed.get('season', '')

        lines = parsed.get('lines', [])
        line_vals = []
        for line in lines:
            line_vals.append({
                'wizard_id': self.id,
                'line_number': line['line_number'],
                'style_number': line['style_number'],
                'style_name': line.get('style_name', ''),
                'color': line.get('color', ''),
                'color_code': line.get('color_code', ''),
                'size': line.get('size', ''),
                'quantity': line.get('quantity', 0),
                'wholesale_price': line.get('wholesale_price', 0),
                'retail_price': line.get('retail_price', 0),
            })

        self.env['b2b.order.import.wizard.line'].create(line_vals)

        summary = parsed.get('summary', {})
        info_html = (
            '<div style="padding: 10px;">'
            '<table class="table table-sm table-bordered" '
            'style="max-width: 600px;">'
            '<tr><th>Temporada</th><td>{season}</td></tr>'
            '<tr><th>Inicio envío</th><td>{start}</td></tr>'
            '<tr><th>Fin envío</th><td>{end}</td></tr>'
            '<tr><th>Total líneas</th><td>{lines}</td></tr>'
            '<tr><th>Total unidades</th><td>{units}</td></tr>'
            '<tr><th>Total importe</th><td>{total:.2f} EUR</td></tr>'
            '</table></div>'
        ).format(
            season=parsed.get('season', '-'),
            start=parsed.get('ship_start', '-'),
            end=parsed.get('ship_end', '-'),
            lines=len(lines),
            units=sum(l['quantity'] for l in lines),
            total=sum(l['quantity'] * l['wholesale_price'] for l in lines),
        )
        self.preview_info = info_html

    # =========================================================================
    # Previsualización — MIRRI
    # =========================================================================
    def _populate_preview_mirri(self, parsed):
        """Rellena las líneas de previsualización para un fichero MIRRI."""
        self.preview_line_ids.unlink()

        brands = parsed.get('brands', [])
        self.detected_brand = ', '.join(brands[:5]) if brands else ''
        self.detected_po_number = ''

        products = parsed.get('products', [])
        # Limitar preview a 500 líneas para rendimiento del wizard
        preview_products = products[:500]
        line_vals = []
        for prod in preview_products:
            line_vals.append({
                'wizard_id': self.id,
                'line_number': prod['line_number'],
                'style_number': prod.get('designer_id', ''),
                'style_name': prod.get('product_name', '') or prod.get('designer_id', ''),
                'color': prod.get('color_description', '') or prod.get('color_code', ''),
                'color_code': prod.get('color_code', ''),
                'size': prod.get('size', ''),
                'quantity': prod.get('stock', 0),
                'wholesale_price': prod.get('supply_price', 0),
                'retail_price': prod.get('retail_price', 0),
            })

        self.env['b2b.order.import.wizard.line'].create(line_vals)

        info_html = (
            '<div style="padding: 10px;">'
            '<div class="alert alert-info">'
            '<strong>MIRRI es un catálogo de stock.</strong> '
            'No se creará un pedido de compra. Se crearán/actualizarán '
            'productos y su stock disponible.'
            '</div>'
            '<table class="table table-sm table-bordered" '
            'style="max-width: 600px;">'
            '<tr><th>Marcas</th><td>{brands}</td></tr>'
            '<tr><th>Total filas</th><td>{total}</td></tr>'
            '<tr><th>Stock total</th><td>{stock:.0f}</td></tr>'
            '<tr><th>Previsualizando</th><td>{preview} de {total} filas</td></tr>'
            '</table></div>'
        ).format(
            brands=', '.join(brands[:10]) if brands else '-',
            total=parsed.get('total_rows', 0),
            stock=parsed.get('total_stock', 0),
            preview=len(preview_products),
        )
        self.preview_info = info_html

    # =========================================================================
    # Importación — JOOR / The New Black
    # =========================================================================
    def _import_joor(self, parsed, log):
        """Importa un pedido JOOR: crea productos y pedido de compra."""
        lines = parsed.get('lines', [])
        if not lines:
            raise UserError(_("El fichero no contiene líneas de producto."))

        # Validar proveedor
        supplier = self.supplier_id
        if not supplier:
            raise UserError(_("Debe seleccionar un proveedor."))

        # Crear pedido de compra
        po_vals = {
            'partner_id': supplier.id,
            'company_id': self.company_id.id,
            'partner_ref': parsed.get('po_number', ''),
            'notes': 'Importado desde %s — PO# %s\nMarca: %s' % (
                self.platform.upper() if self.platform != 'thenewblack' else 'The New Black',
                parsed.get('po_number', ''),
                parsed.get('brand', ''),
            ),
        }
        # Asignar picking_type_id si hay almacén seleccionado
        if self.warehouse_id:
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('code', '=', 'incoming'),
            ], limit=1)
            if picking_type:
                po_vals['picking_type_id'] = picking_type.id

        purchase_order = self.env['purchase.order'].create(po_vals)

        products_created = 0
        products_matched = 0
        lines_imported = 0
        log_lines = []

        for line in lines:
            try:
                product, was_created = self._find_or_create_product(
                    style_number=line['style_number'],
                    style_name=line.get('style_name', ''),
                    color=line.get('color', ''),
                    color_code=line.get('color_code', ''),
                    size=line.get('size', ''),
                    wholesale_price=line.get('wholesale_price', 0),
                    retail_price=line.get('retail_price', 0),
                    supplier=supplier,
                    materials=line.get('materials', ''),
                )

                if was_created:
                    products_created += 1
                else:
                    products_matched += 1

                # Crear línea de pedido de compra
                pol_vals = {
                    'order_id': purchase_order.id,
                    'product_id': product.id,
                    'product_qty': line['quantity'],
                    'price_unit': line['wholesale_price'],
                }
                self.env['purchase.order.line'].create(pol_vals)
                lines_imported += 1

                log_lines.append({
                    'log_id': log.id,
                    'line_number': line['line_number'],
                    'style_number': line['style_number'],
                    'color': line.get('color', ''),
                    'size': line.get('size', ''),
                    'quantity': line['quantity'],
                    'price': line['wholesale_price'],
                    'retail_price': line.get('retail_price', 0),
                    'product_id': product.id,
                    'state': 'created' if was_created else 'ok',
                    'message': 'Producto creado' if was_created else 'Producto encontrado',
                })

            except Exception as e:
                _logger.warning(
                    "Error procesando línea %s: %s",
                    line.get('line_number'),
                    str(e),
                )
                log_lines.append({
                    'log_id': log.id,
                    'line_number': line.get('line_number', 0),
                    'style_number': line.get('style_number', ''),
                    'color': line.get('color', ''),
                    'size': line.get('size', ''),
                    'quantity': line.get('quantity', 0),
                    'price': line.get('wholesale_price', 0),
                    'retail_price': line.get('retail_price', 0),
                    'state': 'error',
                    'message': str(e)[:200],
                })

        # Crear log lines en bloque
        if log_lines:
            self.env['b2b.import.log.line'].create(log_lines)

        log.write({
            'purchase_order_id': purchase_order.id,
            'products_created': products_created,
            'products_matched': products_matched,
            'lines_imported': lines_imported,
        })

    # =========================================================================
    # Importación — NuORDER
    # =========================================================================
    def _import_nuorder(self, parsed, log):
        """Importa un pedido NuORDER: crea productos y pedido de compra."""
        lines = parsed.get('lines', [])
        if not lines:
            raise UserError(_("El fichero no contiene líneas de producto."))

        supplier = self.supplier_id
        if not supplier:
            raise UserError(_("Debe seleccionar un proveedor."))

        po_vals = {
            'partner_id': supplier.id,
            'company_id': self.company_id.id,
            'notes': 'Importado desde NuORDER\nTemporada: %s' % (
                parsed.get('season', ''),
            ),
        }
        if self.warehouse_id:
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', self.warehouse_id.id),
                ('code', '=', 'incoming'),
            ], limit=1)
            if picking_type:
                po_vals['picking_type_id'] = picking_type.id

        purchase_order = self.env['purchase.order'].create(po_vals)

        products_created = 0
        products_matched = 0
        lines_imported = 0
        log_lines = []

        for line in lines:
            try:
                product, was_created = self._find_or_create_product(
                    style_number=line['style_number'],
                    style_name=line.get('style_name', '') or line.get('description', ''),
                    color=line.get('color', ''),
                    color_code=line.get('color_code', ''),
                    size=line.get('size', ''),
                    wholesale_price=line.get('wholesale_price', 0),
                    retail_price=line.get('retail_price', 0),
                    supplier=supplier,
                    materials=line.get('fabric', ''),
                    category_name=line.get('category', ''),
                    department=line.get('department', ''),
                )

                if was_created:
                    products_created += 1
                else:
                    products_matched += 1

                pol_vals = {
                    'order_id': purchase_order.id,
                    'product_id': product.id,
                    'product_qty': line['quantity'],
                    'price_unit': line['wholesale_price'],
                }
                self.env['purchase.order.line'].create(pol_vals)
                lines_imported += 1

                log_lines.append({
                    'log_id': log.id,
                    'line_number': line['line_number'],
                    'style_number': line['style_number'],
                    'color': line.get('color', ''),
                    'size': line.get('size', ''),
                    'quantity': line['quantity'],
                    'price': line['wholesale_price'],
                    'retail_price': line.get('retail_price', 0),
                    'product_id': product.id,
                    'state': 'created' if was_created else 'ok',
                    'message': 'Producto creado' if was_created else 'Producto encontrado',
                })

            except Exception as e:
                _logger.warning(
                    "Error procesando línea NuORDER %s: %s",
                    line.get('line_number'),
                    str(e),
                )
                log_lines.append({
                    'log_id': log.id,
                    'line_number': line.get('line_number', 0),
                    'style_number': line.get('style_number', ''),
                    'color': line.get('color', ''),
                    'size': line.get('size', ''),
                    'quantity': line.get('quantity', 0),
                    'price': line.get('wholesale_price', 0),
                    'retail_price': line.get('retail_price', 0),
                    'state': 'error',
                    'message': str(e)[:200],
                })

        if log_lines:
            self.env['b2b.import.log.line'].create(log_lines)

        log.write({
            'purchase_order_id': purchase_order.id,
            'products_created': products_created,
            'products_matched': products_matched,
            'lines_imported': lines_imported,
        })

    # =========================================================================
    # Importación — MIRRI (catálogo/stock)
    # =========================================================================
    def _import_mirri(self, parsed, log):
        """
        Importa un catálogo MIRRI: crea/actualiza productos y opcionalmente stock.
        NO crea pedido de compra.
        """
        products_list = parsed.get('products', [])
        if not products_list:
            raise UserError(_("El fichero no contiene productos."))

        products_created = 0
        products_matched = 0
        lines_imported = 0
        log_lines = []

        # Agrupar por designer_id + color_code para crear templates eficientemente
        templates_map = {}  # key: (designer_id, color_code) → list of size entries
        for prod in products_list:
            key = (prod['designer_id'], prod['color_code'])
            if key not in templates_map:
                templates_map[key] = {
                    'info': prod,
                    'sizes': [],
                }
            templates_map[key]['sizes'].append(prod)

        # Buscar proveedor para supplierinfo
        supplier = self.supplier_id  # Puede ser None para MIRRI

        for key, data in templates_map.items():
            info = data['info']
            sizes = data['sizes']

            for size_entry in sizes:
                try:
                    product, was_created = self._find_or_create_product(
                        style_number=info['designer_id'],
                        style_name=info.get('product_name', '') or info['designer_id'],
                        color=info.get('color_description', '') or info['color_code'],
                        color_code=info['color_code'],
                        size=size_entry['size'],
                        wholesale_price=size_entry.get('supply_price', 0),
                        retail_price=size_entry.get('retail_price', 0),
                        supplier=supplier,
                        materials=info.get('composition', ''),
                        category_name=info.get('category_level_3', '') or info.get('category_level_2', ''),
                        department=info.get('category_level_1', ''),
                        brand_name=info.get('brand_name', ''),
                        product_description=info.get('product_description', ''),
                    )

                    if was_created:
                        products_created += 1
                    else:
                        products_matched += 1
                    lines_imported += 1

                    log_lines.append({
                        'log_id': log.id,
                        'line_number': size_entry['line_number'],
                        'style_number': info['designer_id'],
                        'color': info.get('color_description', '') or info['color_code'],
                        'size': size_entry['size'],
                        'quantity': size_entry.get('stock', 0),
                        'price': size_entry.get('supply_price', 0),
                        'retail_price': size_entry.get('retail_price', 0),
                        'product_id': product.id,
                        'state': 'created' if was_created else 'ok',
                        'message': 'Producto creado' if was_created else 'Producto encontrado',
                    })

                except Exception as e:
                    _logger.warning(
                        "Error procesando MIRRI línea %s: %s",
                        size_entry.get('line_number'),
                        str(e),
                    )
                    log_lines.append({
                        'log_id': log.id,
                        'line_number': size_entry.get('line_number', 0),
                        'style_number': info.get('designer_id', ''),
                        'color': info.get('color_description', '') or info.get('color_code', ''),
                        'size': size_entry.get('size', ''),
                        'quantity': size_entry.get('stock', 0),
                        'price': size_entry.get('supply_price', 0),
                        'retail_price': size_entry.get('retail_price', 0),
                        'state': 'error',
                        'message': str(e)[:200],
                    })

        if log_lines:
            self.env['b2b.import.log.line'].create(log_lines)

        log.write({
            'products_created': products_created,
            'products_matched': products_matched,
            'lines_imported': lines_imported,
        })

    # =========================================================================
    # Lógica de búsqueda / creación de productos
    # =========================================================================
    def _find_or_create_product(
        self,
        style_number,
        style_name,
        color,
        color_code,
        size,
        wholesale_price,
        retail_price,
        supplier=None,
        materials='',
        category_name='',
        department='',
        brand_name='',
        product_description='',
    ):
        """
        Busca un producto existente o lo crea si auto_create_products está activo.

        Lógica de búsqueda:
        1. Por referencia de proveedor (product.supplierinfo.product_code)
        2. Por default_code del template
        3. Por nombre (último recurso)

        Para variantes: busca el template, luego la variante con talla + color.

        :return: tuple (product.product, was_created: bool)
        """
        ProductProduct = self.env['product.product']
        ProductTemplate = self.env['product.template']
        SupplierInfo = self.env['product.supplierinfo']

        # -----------------------------------------------------------------
        # 1. Buscar por referencia de proveedor
        # -----------------------------------------------------------------
        if supplier:
            supplierinfo = SupplierInfo.search([
                ('partner_id', '=', supplier.id),
                ('product_code', '=', style_number),
            ], limit=1)
            if supplierinfo:
                template = supplierinfo.product_tmpl_id
                if template:
                    variant = self._find_variant_by_attributes(
                        template, size, color, color_code
                    )
                    if variant:
                        return variant, False

        # -----------------------------------------------------------------
        # 2. Buscar por default_code
        # -----------------------------------------------------------------
        templates = ProductTemplate.search([
            ('default_code', '=', style_number),
        ])
        if templates:
            template = templates[0]
            variant = self._find_variant_by_attributes(
                template, size, color, color_code
            )
            if variant:
                return variant, False

        # También buscar variantes directamente por default_code compuesto
        # Formato típico: STYLE-COLOR-SIZE
        composite_codes = [
            '%s-%s-%s' % (style_number, color_code, size),
            '%s/%s/%s' % (style_number, color_code, size),
            '%s %s %s' % (style_number, color_code, size),
        ]
        for code in composite_codes:
            variant = ProductProduct.search([
                ('default_code', '=', code),
            ], limit=1)
            if variant:
                return variant, False

        # -----------------------------------------------------------------
        # 3. Buscar por nombre (último recurso)
        # -----------------------------------------------------------------
        if style_name:
            templates = ProductTemplate.search([
                ('name', '=ilike', style_name),
            ], limit=1)
            if templates:
                variant = self._find_variant_by_attributes(
                    templates[0], size, color, color_code
                )
                if variant:
                    return variant, False

        # -----------------------------------------------------------------
        # 4. Crear producto si está activada la opción
        # -----------------------------------------------------------------
        if not self.auto_create_products:
            raise UserError(
                _("Producto no encontrado: %s (color: %s, talla: %s). "
                  "Active la opción 'Crear productos automáticamente' "
                  "para crearlo.") % (style_number, color, size)
            )

        product = self._create_product_with_variant(
            style_number=style_number,
            style_name=style_name,
            color=color,
            color_code=color_code,
            size=size,
            wholesale_price=wholesale_price,
            retail_price=retail_price,
            supplier=supplier,
            materials=materials,
            category_name=category_name,
            department=department,
            brand_name=brand_name,
            product_description=product_description,
        )
        return product, True

    def _find_variant_by_attributes(self, template, size, color, color_code=''):
        """
        Busca una variante del template con los atributos Talla y Color indicados.
        Si no la encuentra, intenta añadir los atributos al template
        (lo que auto-crea la variante).
        """
        if not template.product_variant_ids:
            return None

        # Si el template solo tiene una variante y no tiene atributos,
        # devolver esa variante directamente
        if (
            len(template.product_variant_ids) == 1
            and not template.attribute_line_ids
        ):
            return template.product_variant_ids[0]

        # Buscar variante con atributos coincidentes
        for variant in template.product_variant_ids:
            size_match = False
            color_match = False
            has_size_attr = False
            has_color_attr = False

            for ptav in variant.product_template_attribute_value_ids:
                attr_name = ptav.attribute_id.name.lower().strip()
                val_name = ptav.product_attribute_value_id.name.strip()

                if attr_name in ('talla', 'size', 'taille'):
                    has_size_attr = True
                    if val_name == str(size).strip():
                        size_match = True
                elif attr_name in ('color', 'colour', 'colore'):
                    has_color_attr = True
                    # Comparar por nombre o código
                    if (
                        val_name.lower() == str(color).lower().strip()
                        or val_name == str(color_code).strip()
                    ):
                        color_match = True

            # Si el template no tiene un tipo de atributo, considerarlo match
            if not has_size_attr:
                size_match = True
            if not has_color_attr:
                color_match = True

            if size_match and color_match:
                return variant

        return None

    def _create_product_with_variant(
        self,
        style_number,
        style_name,
        color,
        color_code,
        size,
        wholesale_price,
        retail_price,
        supplier=None,
        materials='',
        category_name='',
        department='',
        brand_name='',
        product_description='',
    ):
        """
        Crea un product.template con atributos Talla y Color,
        y devuelve la variante correspondiente.
        """
        ProductTemplate = self.env['product.template']
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']

        # Buscar o crear atributo Talla
        size_attr = ProductAttribute.search([
            ('name', 'in', ['Talla', 'Size', 'Taille']),
        ], limit=1)
        if not size_attr:
            size_attr = ProductAttribute.create({
                'name': 'Talla',
                'display_type': 'select',
                'create_variant': 'always',
            })

        # Buscar o crear atributo Color
        color_attr = ProductAttribute.search([
            ('name', 'in', ['Color', 'Colour', 'Colore']),
        ], limit=1)
        if not color_attr:
            color_attr = ProductAttribute.create({
                'name': 'Color',
                'display_type': 'color',
                'create_variant': 'always',
            })

        # Buscar o crear valor de talla
        size_value = self._get_or_create_attribute_value(size_attr, str(size).strip())

        # Buscar o crear valor de color
        color_display = color or color_code
        if not color_display:
            color_display = 'Sin color'
        color_value = self._get_or_create_attribute_value(color_attr, color_display)

        # Verificar si ya existe un template con este style_number
        # (otro hilo pudo crearlo en paralelo o mismo fichero con otra talla)
        existing_template = ProductTemplate.search([
            ('default_code', '=', style_number),
        ], limit=1)

        if existing_template:
            # Añadir atributos que falten al template existente
            self._ensure_template_has_attribute_value(
                existing_template, size_attr, size_value
            )
            self._ensure_template_has_attribute_value(
                existing_template, color_attr, color_value
            )
            # Buscar la variante recién creada/existente
            variant = self._find_variant_by_attributes(
                existing_template, size, color, color_code
            )
            if variant:
                return variant
            # Si no se encuentra, devolver la primera variante como fallback
            if existing_template.product_variant_ids:
                return existing_template.product_variant_ids[0]

        # Construir nombre del producto
        product_name = style_name or style_number
        if brand_name and brand_name.lower() not in product_name.lower():
            product_name = '%s - %s' % (brand_name, product_name)

        # Buscar categoría de producto
        categ_id = self._find_or_create_category(category_name, department)

        # Construir descripción
        description_parts = []
        if product_description:
            description_parts.append(product_description)
        if materials:
            description_parts.append('Composición: %s' % materials)

        # Crear template
        template_vals = {
            'name': product_name,
            'default_code': style_number,
            'type': 'consu',
            'list_price': retail_price,
            'standard_price': wholesale_price,
            'purchase_ok': True,
            'sale_ok': True,
            'description_purchase': '\n'.join(description_parts) if description_parts else False,
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': size_attr.id,
                    'value_ids': [(4, size_value.id)],
                }),
                (0, 0, {
                    'attribute_id': color_attr.id,
                    'value_ids': [(4, color_value.id)],
                }),
            ],
        }

        if categ_id:
            template_vals['categ_id'] = categ_id

        template = ProductTemplate.create(template_vals)

        # Crear supplierinfo
        if supplier:
            self.env['product.supplierinfo'].create({
                'partner_id': supplier.id,
                'product_tmpl_id': template.id,
                'product_code': style_number,
                'price': wholesale_price,
                'min_qty': 1,
            })

        # Buscar la variante creada
        variant = self._find_variant_by_attributes(
            template, size, color, color_code
        )
        if variant:
            return variant

        # Fallback: devolver primera variante
        if template.product_variant_ids:
            return template.product_variant_ids[0]

        raise UserError(
            _("No se pudo crear la variante para %s (talla: %s, color: %s)")
            % (style_number, size, color)
        )

    def _get_or_create_attribute_value(self, attribute, value_name):
        """Busca o crea un valor de atributo."""
        ProductAttributeValue = self.env['product.attribute.value']
        value = ProductAttributeValue.search([
            ('attribute_id', '=', attribute.id),
            ('name', '=', value_name),
        ], limit=1)
        if not value:
            value = ProductAttributeValue.create({
                'attribute_id': attribute.id,
                'name': value_name,
            })
        return value

    def _ensure_template_has_attribute_value(self, template, attribute, attr_value):
        """
        Asegura que un template tiene una línea de atributo con el valor indicado.
        Si la línea existe pero le falta el valor, lo añade.
        Si la línea no existe, la crea.
        """
        attr_line = template.attribute_line_ids.filtered(
            lambda l: l.attribute_id.id == attribute.id
        )
        if attr_line:
            if attr_value.id not in attr_line.value_ids.ids:
                attr_line.write({
                    'value_ids': [(4, attr_value.id)],
                })
        else:
            self.env['product.template.attribute.line'].create({
                'product_tmpl_id': template.id,
                'attribute_id': attribute.id,
                'value_ids': [(4, attr_value.id)],
            })

    def _find_or_create_category(self, category_name, department=''):
        """Busca o crea una categoría de producto."""
        if not category_name:
            return False

        ProductCategory = self.env['product.category']

        # Buscar categoría existente por nombre
        category = ProductCategory.search([
            ('name', '=ilike', category_name),
        ], limit=1)

        if category:
            return category.id

        # Si hay departamento, crear jerarquía
        parent_id = False
        if department:
            parent = ProductCategory.search([
                ('name', '=ilike', department),
            ], limit=1)
            if not parent:
                parent = ProductCategory.create({'name': department})
            parent_id = parent.id

        category = ProductCategory.create({
            'name': category_name,
            'parent_id': parent_id,
        })
        return category.id

    def _find_supplier_by_name(self, brand_name):
        """
        Intenta encontrar un proveedor (res.partner) por nombre de marca.
        Busca coincidencia exacta, luego parcial.
        """
        Partner = self.env['res.partner']

        # Búsqueda exacta
        partner = Partner.search([
            ('name', '=ilike', brand_name),
            ('supplier_rank', '>', 0),
        ], limit=1)
        if partner:
            return partner

        # Búsqueda parcial
        partner = Partner.search([
            ('name', 'ilike', brand_name),
            ('supplier_rank', '>', 0),
        ], limit=1)
        return partner or False

    # =========================================================================
    # Utilidades
    # =========================================================================
    def _reopen_wizard(self):
        """Reabre el wizard en la misma ventana."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class B2bOrderImportWizardLine(models.TransientModel):
    _name = 'b2b.order.import.wizard.line'
    _description = 'Línea de previsualización del wizard de importación B2B'
    _order = 'line_number'

    wizard_id = fields.Many2one(
        comodel_name='b2b.order.import.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    line_number = fields.Integer(
        string='Nº',
    )
    style_number = fields.Char(
        string='Ref. estilo',
    )
    style_name = fields.Char(
        string='Nombre',
    )
    color = fields.Char(
        string='Color',
    )
    color_code = fields.Char(
        string='Cód. color',
    )
    size = fields.Char(
        string='Talla',
    )
    quantity = fields.Float(
        string='Cantidad',
    )
    wholesale_price = fields.Float(
        string='Precio mayorista',
    )
    retail_price = fields.Float(
        string='PVP',
    )
