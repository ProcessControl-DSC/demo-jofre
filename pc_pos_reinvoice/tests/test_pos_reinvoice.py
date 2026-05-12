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

    def test_setting_allow_reinvoice_exists(self):
        self.assertIn("allow_reinvoice", self.env["pos.config"]._fields)

    def test_setting_allow_reinvoice_closed_session_exists(self):
        self.assertIn(
            "allow_reinvoice_closed_session", self.env["pos.config"]._fields
        )

    def test_setting_prompt_email_after_reinvoice_exists(self):
        self.assertIn(
            "prompt_email_after_reinvoice", self.env["pos.config"]._fields
        )

    def test_setting_allow_send_invoice_email_exists(self):
        self.assertIn(
            "allow_send_invoice_email", self.env["pos.config"]._fields
        )

    def test_account_move_smart_button_fields_exist(self):
        am_fields = self.env["account.move"]._fields
        self.assertIn("pc_reinvoice_related_ids", am_fields)
        self.assertIn("pc_reinvoice_related_count", am_fields)
        self.assertIn("pc_reinvoice_role", am_fields)


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
        cls.pos_config.allow_reinvoice = True
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

    def test_blocks_when_disabled_in_config(self):
        self.pos_config.allow_reinvoice = False
        with self.assertRaises(UserError):
            self.order._check_reinvoice_allowed(self.partner_b.id)

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


@tagged("post_install", "-at_install")
class TestPosSendInvoiceEmail(TransactionCase):
    """Validaciones de action_send_invoice_email."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Cliente Email Test",
            "email": "cliente@example.com",
        })
        cls.config = cls.env["pos.config"].search([], limit=1)
        cls.config.allow_send_invoice_email = True
        cls.session = cls.env["pos.session"].create(
            {"config_id": cls.config.id}
        )
        cls.order = cls.env["pos.order"].create({
            "session_id": cls.session.id,
            "partner_id": cls.partner.id,
            "amount_paid": 0.0,
            "amount_total": 0.0,
            "amount_tax": 0.0,
            "amount_return": 0.0,
        })

    def test_blocks_when_disabled_in_config(self):
        self.config.allow_send_invoice_email = False
        with self.assertRaises(UserError):
            self.order.action_send_invoice_email("dest@example.com")

    def test_blocks_when_no_invoice(self):
        self.assertFalse(self.order.account_move)
        with self.assertRaises(UserError):
            self.order.action_send_invoice_email("dest@example.com")

    def test_blocks_when_no_target_email(self):
        self.partner.email = False
        with self.assertRaises(UserError):
            self.order.action_send_invoice_email(False)


@tagged("post_install", "-at_install")
class TestPosReinvoiceLocalizationHooks(TransactionCase):
    """Hooks de localización opcionales (l10n_es / l10n_es_edi_verifactu)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente Refactura Localización"}
        )
        cls.config = cls.env["pos.config"].search([], limit=1)
        cls.session = cls.env["pos.session"].create(
            {"config_id": cls.config.id}
        )
        cls.order = cls.env["pos.order"].create({
            "session_id": cls.session.id,
            "partner_id": cls.partner.id,
            "amount_paid": 0.0,
            "amount_total": 0.0,
            "amount_tax": 0.0,
            "amount_return": 0.0,
        })

    def test_clear_localization_flags_resets_simplified(self):
        if "is_l10n_es_simplified_invoice" not in self.order._fields:
            self.skipTest("l10n_es_pos no instalado en este entorno")
        self.order.is_l10n_es_simplified_invoice = True
        self.order._reinvoice_clear_localization_flags()
        self.assertFalse(self.order.is_l10n_es_simplified_invoice)

    def test_verifactu_refund_reason_returns_false_without_verifactu(self):
        if "l10n_es_edi_verifactu_refund_reason" in self.env[
            "account.move"
        ]._fields:
            self.skipTest("l10n_es_edi_verifactu instalado")
        self.assertFalse(
            self.order._get_reinvoice_verifactu_refund_reason()
        )

    def test_verifactu_refund_reason_R1_when_not_simplified(self):
        if "l10n_es_edi_verifactu_refund_reason" not in self.env[
            "account.move"
        ]._fields:
            self.skipTest("l10n_es_edi_verifactu no instalado")
        if "is_l10n_es_simplified_invoice" in self.order._fields:
            self.order.is_l10n_es_simplified_invoice = False
        self.assertEqual(
            self.order._get_reinvoice_verifactu_refund_reason(),
            "R1",
        )

    def test_verifactu_refund_reason_R5_when_simplified(self):
        if "l10n_es_edi_verifactu_refund_reason" not in self.env[
            "account.move"
        ]._fields:
            self.skipTest("l10n_es_edi_verifactu no instalado")
        if "is_l10n_es_simplified_invoice" not in self.order._fields:
            self.skipTest("l10n_es_pos no instalado")
        self.order.is_l10n_es_simplified_invoice = True
        self.assertEqual(
            self.order._get_reinvoice_verifactu_refund_reason(),
            "R5",
        )
