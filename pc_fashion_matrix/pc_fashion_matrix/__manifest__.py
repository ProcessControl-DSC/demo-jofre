{
    'name': 'Fashion Matrix — Grid Compras/Ventas Moda',
    'version': '19.0.1.0.0',
    'category': 'Supply Chain/Purchase',
    'summary': 'Grid matricial talla×color con distribución por tienda para retail moda',
    'description': """
        Extiende el product_matrix estándar de Odoo para el sector de moda retail.

        Funcionalidades:
        - Campos de moda en pedidos: temporada, género, familia de producto
        - Grid matricial talla×color con totales por fila/columna
        - Distribución automática por tienda (método de Hund)
        - Creación de transferencias internas a tiendas desde el pedido de compra
        - Informes de grid en pedidos impresos
    """,
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
        'data/fashion_data.xml',
        'views/fashion_config_views.xml',
        'views/menus.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pc_fashion_matrix/static/src/scss/fashion_matrix.scss',
            'pc_fashion_matrix/static/src/js/fashion_matrix_dialog.js',
            'pc_fashion_matrix/static/src/js/store_distribution.js',
            'pc_fashion_matrix/static/src/xml/*.xml',
        ],
    },
    'installable': True,
    'application': False,
}
