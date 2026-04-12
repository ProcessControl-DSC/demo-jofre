# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'PC Fashion Matrix',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Enhanced visual product matrix for fashion retail',
    'description': 'Visual order entry grid with product images, color swatches, '
                   'size matrix and store distribution for fashion wholesale.',
    'author': 'Process Control',
    'website': 'https://www.processcontrol.es',
    'license': 'LGPL-3',
    'depends': [
        'purchase_product_matrix',
        'sale_product_matrix',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fashion_season_data.xml',
        'data/fashion_family_data.xml',
        'views/fashion_season_views.xml',
        'views/fashion_product_family_views.xml',
        'views/store_distribution_profile_views.xml',
        'views/product_template_views.xml',
        'views/purchase_order_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pc_fashion_matrix/static/src/scss/fashion_matrix.scss',
            'pc_fashion_matrix/static/src/js/fashion_matrix_distribution.js',
            'pc_fashion_matrix/static/src/js/fashion_matrix_dialog.js',
            'pc_fashion_matrix/static/src/xml/fashion_matrix_dialog.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
