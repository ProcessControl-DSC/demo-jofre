# -*- coding: utf-8 -*-
# Part of Process Control. See LICENSE file for full copyright and licensing details.

{
    'name': 'PC POS Transfers',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Request inter-store stock transfers from POS',
    'description': """
Solicitud de traslados entre tiendas desde el TPV.
Permite a los empleados solicitar productos de otros almacenes
y hacer seguimiento del estado de los traslados directamente
desde la interfaz del punto de venta.
    """,
    'author': 'Process Control',
    'website': 'https://www.processcontrol.es',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pc_pos_transfers/static/src/app/**/*.js',
            'pc_pos_transfers/static/src/app/**/*.xml',
            'pc_pos_transfers/static/src/scss/**/*.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
}
