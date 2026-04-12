# -*- coding: utf-8 -*-
{
    'name': 'PC B2B Order Import',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Importar pedidos de compra desde plataformas B2B de moda (JOOR, NuORDER, MIRRI)',
    'description': """
        Módulo para importar pedidos de compra desde plataformas B2B de moda:
        - JOOR (Excel .xlsx)
        - NuORDER (Excel .xlsx)
        - MIRRI (CSV — catálogo/stock)
        - The New Black (Excel .xlsx)

        Crea automáticamente productos (template + variantes por talla/color)
        y pedidos de compra a partir de los ficheros exportados de las plataformas.
    """,
    'author': 'Process Control',
    'website': 'https://www.processcontrol.es',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'stock',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/b2b_order_import_wizard_views.xml',
        'views/b2b_import_log_views.xml',
        'views/menu.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'installable': True,
    'auto_install': False,
}
