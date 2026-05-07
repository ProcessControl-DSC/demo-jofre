from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosReinvoiceFields(TransactionCase):
    """Smoke tests: campos y settings expuestos por el módulo."""

    def test_field_re_invoiced_exists(self):
        self.assertIn("re_invoiced", self.env["pos.order"]._fields)

    def test_field_reinvoice_ids_exists(self):
        self.assertIn("reinvoice_ids", self.env["pos.order"]._fields)

    def test_setting_allow_reinvoice_closed_session_exists(self):
        self.assertIn(
            "allow_reinvoice_closed_session",
            self.env["pos.config"]._fields,
        )


@tagged("post_install", "-at_install")
class TestPosReinvoiceChecks(TransactionCase):
    """Bloqueos de _check_reinvoice_allowed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a = cls.env["res.partner"].create(
            {"name": "Cliente Refactura A"}
        )
        cls.partner_b = cls.env["res.partner"].create(
            {"name": "Cliente Refactura B"}
        )
        cls.pos_config = cls.env["pos.config"].search([], limit=1)
        cls.pos_config.allow_reinvoice_closed_session = False
        cls.session = cls.env["pos.session"].create(
            {"config_id": cls.pos_config.id}
        )
        cls.order = cls.env["pos.order"].create({
            "session_id": cls.session.id,
            "partner_id": cls.partner_a.id,
            "amount_paid": 0.0,
            "amount_total": 0.0,
            "amount_tax": 0.0,
            "amount_return": 0.0,
        })

    def test_blocks_when_already_reinvoiced(self):
        self.order.re_invoiced = True
        with self.assertRaises(UserError):
            self.order._check_reinvoice_allowed(self.partner_b.id)

    def test_blocks_same_partner(self):
        with self.assertRaises(UserError):
            self.order._check_reinvoice_allowed(self.partner_a.id)

    def test_blocks_without_partner(self):
        with self.assertRaises(UserError):
            self.order._check_reinvoice_allowed(False)

    def test_blocks_closed_session_without_flag(self):
        self.session.state = "closed"
        self.pos_config.allow_reinvoice_closed_session = False
        with self.assertRaises(UserError):
            self.order._check_reinvoice_allowed(self.partner_b.id)

    def test_allows_closed_session_with_flag(self):
        self.session.state = "closed"
        self.pos_config.allow_reinvoice_closed_session = True
        self.assertTrue(
            self.order._check_reinvoice_allowed(self.partner_b.id)
        )

    def test_allows_open_session(self):
        self.assertTrue(
            self.order._check_reinvoice_allowed(self.partner_b.id)
        )
