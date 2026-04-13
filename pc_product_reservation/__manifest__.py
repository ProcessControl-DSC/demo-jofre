# -*- coding: utf-8 -*-
{
    'name': 'PC Product Reservation',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Reserve products for customers from POS with stock blocking',
    'description': """
        Permite a los empleados de tienda reservar variantes de producto específicas
        para clientes identificados directamente desde el TPV. El stock reservado se
        traslada físicamente a una ubicación dedicada ("Reservas Clientes"),
        haciéndolo no disponible para canales online y otras tiendas.
    """,
    'author': 'Process Control',
    'website': 'https://www.processcontrol.es',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'sale_management',
        'stock',
    ],
    'data': [
        'security/product_reservation_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/product_reservation_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
        'report/reservation_report.xml',
        'report/reservation_report_template.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pc_product_reservation/static/src/app/**/*.js',
            'pc_product_reservation/static/src/app/**/*.xml',
            'pc_product_reservation/static/src/scss/**/*.scss',
        ],
    },
    
    'installable': True,
    'auto_install': False,
}
