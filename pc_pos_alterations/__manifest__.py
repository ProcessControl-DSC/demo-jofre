# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

{
    'name': 'PC POS Alterations',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Clothing alterations from POS with repair order tracking',
    'description': """
Gestión de arreglos de ropa desde el TPV.
Permite añadir arreglos como líneas de pedido con precio visible
y descuento del 100% vía tarifa. El seguimiento se realiza mediante
órdenes de reparación estándar del módulo Reparaciones (repair).
    """,
    'author': 'Process Control',
    'website': 'https://www.processcontrol.es',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'stock',
        'repair',
    ],
    'data': [
        'security/alteration_security.xml',
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/alteration_type_data.xml',
        'views/repair_order_views.xml',
        'views/alteration_type_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pc_pos_alterations/static/src/app/**/*.js',
            'pc_pos_alterations/static/src/app/**/*.xml',
            'pc_pos_alterations/static/src/scss/**/*.scss',
        ],
    },
    'post_init_hook': '_create_workshop_locations',
    'installable': True,
    'auto_install': False,
}
