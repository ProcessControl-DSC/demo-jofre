{
    'name': 'PC POS Empty Product Screen',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'POS shows no products until a category is selected',
    'description': 'The POS product screen starts empty. Products only appear when the user selects a category or searches.',
    'author': 'Process Control',
    'website': 'https://www.processcontrol.es',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pc_pos_empty_screen/static/src/app/screens/product_screen/product_screen_extend.js',
            'pc_pos_empty_screen/static/src/app/screens/product_screen/product_screen_extend.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
