{
    "name": "POS - Line Source Location",
    "version": "19.0.1.2.0",
    "summary": "Select the source stock location per POS order line",
    "description": """
Allow cashiers to select, for each line of a POS ticket, the internal
stock location from which the product is picked. The selected location
propagates to the stock move lines of the picking generated at the end
of the session, overriding the default removal strategy.
    """,
    "author": "Process Control",
    "website": "https://www.processcontrol.es",
    "license": "LGPL-3",
    "category": "Sales/Point of Sale",
    "depends": [
        "point_of_sale",
        "stock",
    ],
    "data": [
        "views/pos_config_views.xml",
        "views/pos_order_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pc_pos_line_location/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
