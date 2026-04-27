from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosLineLocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Location = cls.env["stock.location"]
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.shelf_a = Location.create(
            {
                "name": "Shelf A",
                "usage": "internal",
                "location_id": cls.stock_location.id,
            }
        )
        cls.shelf_b = Location.create(
            {
                "name": "Shelf B",
                "usage": "internal",
                "location_id": cls.stock_location.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Book",
                "type": "consu",
                "is_storable": True,
                "list_price": 10.0,
                "available_in_pos": True,
            }
        )
        Quant = cls.env["stock.quant"].with_context(inventory_mode=True)
        Quant.create(
            {
                "product_id": cls.product.id,
                "location_id": cls.shelf_a.id,
                "inventory_quantity": 5.0,
            }
        ).action_apply_inventory()
        Quant.create(
            {
                "product_id": cls.product.id,
                "location_id": cls.shelf_b.id,
                "inventory_quantity": 3.0,
            }
        ).action_apply_inventory()

        cls.pos_config = cls.env["pos.config"].search([], limit=1)
        cls.pos_config.picking_type_id.default_location_src_id = cls.stock_location

    def test_field_exists_on_line(self):
        self.assertIn("location_id", self.env["pos.order.line"]._fields)

    def test_setting_on_config(self):
        self.assertIn(
            "allow_line_location_selection", self.env["pos.config"]._fields
        )

    def test_load_pos_data_adds_stock_models(self):
        self.pos_config.allow_line_location_selection = True
        session = self.env["pos.session"].create({"config_id": self.pos_config.id})
        models = session._load_pos_data_models(self.pos_config)
        self.assertIn("stock.location", models)
        self.assertIn("stock.quant", models)

    def test_load_pos_data_models_skipped_when_disabled(self):
        self.pos_config.allow_line_location_selection = False
        session = self.env["pos.session"].create({"config_id": self.pos_config.id})
        models = session._load_pos_data_models(self.pos_config)
        self.assertNotIn("stock.location", models)
        self.assertNotIn("stock.quant", models)

    def test_load_pos_data_domain_filters_to_children(self):
        domain = self.env["stock.location"]._load_pos_data_domain(
            {}, self.pos_config
        )
        located = self.env["stock.location"].search(domain)
        self.assertIn(self.shelf_a, located)
        self.assertIn(self.shelf_b, located)
        for loc in located:
            self.assertEqual(loc.usage, "internal")

    def test_quant_domain_filters_by_source_and_positive(self):
        domain = self.env["stock.quant"]._load_pos_data_domain(
            {}, self.pos_config
        )
        quants = self.env["stock.quant"].search(domain)
        for q in quants:
            self.assertGreater(q.quantity, 0)
            self.assertEqual(q.location_id.usage, "internal")

    def test_stock_move_respects_line_location(self):
        session = self.env["pos.session"].create(
            {"config_id": self.pos_config.id}
        )
        session.action_pos_session_open()

        order = self.env["pos.order"].create(
            {
                "session_id": session.id,
                "company_id": self.env.company.id,
                "amount_total": 20.0,
                "amount_tax": 0.0,
                "amount_paid": 20.0,
                "amount_return": 0.0,
            }
        )
        self.env["pos.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "qty": 1.0,
                "price_unit": 10.0,
                "price_subtotal": 10.0,
                "price_subtotal_incl": 10.0,
                "location_id": self.shelf_a.id,
            }
        )
        self.env["pos.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "qty": 1.0,
                "price_unit": 10.0,
                "price_subtotal": 10.0,
                "price_subtotal_incl": 10.0,
                "location_id": self.shelf_b.id,
            }
        )

        order._create_order_picking()
        picking = order.picking_ids
        self.assertTrue(picking, "Picking should be generated")

        moves = picking.move_ids
        self.assertEqual(
            len(moves), 2, "Expected one move per chosen location"
        )
        move_locations = moves.mapped("location_id")
        self.assertIn(self.shelf_a, move_locations)
        self.assertIn(self.shelf_b, move_locations)

    def test_line_without_location_uses_default(self):
        session = self.env["pos.session"].create(
            {"config_id": self.pos_config.id}
        )
        session.action_pos_session_open()

        order = self.env["pos.order"].create(
            {
                "session_id": session.id,
                "company_id": self.env.company.id,
                "amount_total": 10.0,
                "amount_tax": 0.0,
                "amount_paid": 10.0,
                "amount_return": 0.0,
            }
        )
        self.env["pos.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "qty": 1.0,
                "price_unit": 10.0,
                "price_subtotal": 10.0,
                "price_subtotal_incl": 10.0,
            }
        )

        order._create_order_picking()
        picking = order.picking_ids
        self.assertTrue(picking)
        moves = picking.move_ids
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves.location_id, self.stock_location)

    def test_location_outside_source_is_rejected_silently(self):
        outside = self.env["stock.location"].create(
            {
                "name": "Outside Warehouse",
                "usage": "internal",
            }
        )
        session = self.env["pos.session"].create(
            {"config_id": self.pos_config.id}
        )
        session.action_pos_session_open()

        order = self.env["pos.order"].create(
            {
                "session_id": session.id,
                "company_id": self.env.company.id,
                "amount_total": 10.0,
                "amount_tax": 0.0,
                "amount_paid": 10.0,
                "amount_return": 0.0,
            }
        )
        self.env["pos.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "qty": 1.0,
                "price_unit": 10.0,
                "price_subtotal": 10.0,
                "price_subtotal_incl": 10.0,
                "location_id": outside.id,
            }
        )

        order._create_order_picking()
        picking = order.picking_ids
        self.assertTrue(picking)
        moves = picking.move_ids
        self.assertEqual(
            moves.location_id,
            self.stock_location,
            "Location not child of source must fall back to default",
        )
