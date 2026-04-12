# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


FASHION_GENDER_SELECTION = [
    ('man', 'Man'),
    ('woman', 'Woman'),
    ('boy', 'Boy'),
    ('girl', 'Girl'),
    ('baby', 'Baby'),
    ('unisex', 'Unisex'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fashion_season_id = fields.Many2one(
        comodel_name='fashion.season',
        string='Season',
        help='Fashion season this product belongs to',
    )
    fashion_family_id = fields.Many2one(
        comodel_name='fashion.product.family',
        string='Family',
        help='Fashion product family (e.g. Pantalones, Camisas)',
    )
    fashion_gender = fields.Selection(
        selection=FASHION_GENDER_SELECTION,
        string='Gender',
        help='Target gender for this fashion product',
    )
    fashion_supplier_style = fields.Char(
        string='Supplier Style Code',
        help="Supplier's style reference code",
    )
    fashion_supplier_fabric = fields.Char(
        string='Supplier Fabric Code',
        help="Supplier's fabric reference code",
    )

    @api.model
    def _get_fashion_matrix_data(self, product_template_id):
        """Return all data needed to render the fashion matrix dialog.

        This method is called from the OWL component via RPC.
        Returns a dictionary with product info, attributes (colors/sizes),
        images and variant data structured for the matrix grid.
        """
        template = self.browse(product_template_id)
        if not template.exists():
            return {}

        # Gather product images
        images = []
        if template.image_1920:
            images.append({
                'id': template.id,
                'src': f'/web/image/product.template/{template.id}/image_1920',
                'is_main': True,
            })
        # Extra images field comes from website_sale; handle gracefully if absent
        if hasattr(template, 'product_template_image_ids'):
            for image in template.product_template_image_ids:
                images.append({
                    'id': image.id,
                    'src': f'/web/image/product.image/{image.id}/image_1920',
                    'is_main': False,
                })

        # Identify color and size attributes
        color_attr = None
        size_attr = None
        colors = []
        sizes = []

        for attr_line in template.attribute_line_ids:
            attr = attr_line.attribute_id
            # Detect color attribute by type or name heuristics
            if attr.display_type == 'color' or 'color' in attr.name.lower() or 'colour' in attr.name.lower():
                color_attr = attr
                for val in attr_line.value_ids:
                    colors.append({
                        'id': val.id,
                        'name': val.name,
                        'html_color': val.html_color or '#CCCCCC',
                        'is_custom': val.is_custom,
                    })
            # Detect size attribute by name heuristics
            elif 'size' in attr.name.lower() or 'talla' in attr.name.lower() or 'taille' in attr.name.lower():
                size_attr = attr
                for val in attr_line.value_ids:
                    sizes.append({
                        'id': val.id,
                        'name': val.name,
                    })

        # Build variant map: {color_id}_{size_id} -> product.product info
        variant_map = {}
        for variant in template.product_variant_ids:
            color_val = None
            size_val = None
            for ptav in variant.product_template_attribute_value_ids:
                if color_attr and ptav.attribute_id.id == color_attr.id:
                    color_val = ptav.product_attribute_value_id.id
                elif size_attr and ptav.attribute_id.id == size_attr.id:
                    size_val = ptav.product_attribute_value_id.id
            if color_val and size_val:
                key = f"{color_val}_{size_val}"
                variant_map[key] = {
                    'product_id': variant.id,
                    'default_code': variant.default_code or '',
                    'barcode': variant.barcode or '',
                    'qty_available': variant.qty_available,
                }

        # Supplier / Brand info
        seller_name = ''
        seller_price = 0.0
        if template.seller_ids:
            main_seller = template.seller_ids[0]
            seller_name = main_seller.partner_id.name or ''
            seller_price = main_seller.price

        result = {
            'id': template.id,
            'name': template.name,
            'default_code': template.default_code or '',
            'list_price': template.list_price,
            'standard_price': template.standard_price,
            'seller_name': seller_name,
            'seller_price': seller_price,
            'season': template.fashion_season_id.name or '',
            'season_code': template.fashion_season_id.code or '',
            'family': template.fashion_family_id.name or '',
            'gender': template.fashion_gender or '',
            'gender_display': dict(FASHION_GENDER_SELECTION).get(template.fashion_gender, ''),
            'supplier_style': template.fashion_supplier_style or '',
            'supplier_fabric': template.fashion_supplier_fabric or '',
            'images': images,
            'colors': colors,
            'sizes': sizes,
            'variant_map': variant_map,
            'currency_symbol': template.currency_id.symbol or '\u20ac',
            'currency_position': template.currency_id.position or 'after',
        }

        return result

    @api.model
    def _get_distribution_profiles(self):
        """Return available distribution profiles for the matrix dialog."""
        profiles = self.env['store.distribution.profile'].search([('active', '=', True)])
        result = []
        for profile in profiles:
            lines = []
            for line in profile.line_ids:
                lines.append({
                    'warehouse_id': line.warehouse_id.id,
                    'warehouse_name': line.warehouse_id.name,
                    'percentage': line.percentage,
                })
            result.append({
                'id': profile.id,
                'name': profile.name,
                'lines': lines,
            })
        return result
