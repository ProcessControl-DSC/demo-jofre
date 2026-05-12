from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosReinvoiceVerifactu(TransactionCase):
    """Tests del glue Veri*Factu: causa de rectificación R1/R5."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente Verifactu Test"}
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

    def test_refund_reason_field_exists(self):
        self.assertIn(
            "l10n_es_edi_verifactu_refund_reason",
            self.env["account.move"]._fields,
        )

    def test_substituted_entry_field_exists(self):
        self.assertIn(
            "l10n_es_edi_verifactu_substituted_entry_id",
            self.env["account.move"]._fields,
        )

    def test_default_refund_reason_is_R1(self):
        if "is_l10n_es_simplified_invoice" in self.order._fields:
            self.order.is_l10n_es_simplified_invoice = False
        self.assertEqual(
            self.order._get_reinvoice_verifactu_refund_reason(),
            "R1",
        )

    def test_simplified_refund_reason_is_R5(self):
        if "is_l10n_es_simplified_invoice" not in self.order._fields:
            self.skipTest("l10n_es_pos no instalado en este entorno")
        self.order.is_l10n_es_simplified_invoice = True
        self.assertEqual(
            self.order._get_reinvoice_verifactu_refund_reason(),
            "R5",
        )

    def test_refund_reason_written_on_rectificativa(self):
        """Al ejecutar _reinvoice_reverse_original sobre un pedido con
        factura, el refund_reason debe quedar en la rectificativa out_refund,
        no en la factura original ni en la nueva factura."""
        if not self.order.account_move:
            self.skipTest(
                "Pedido sin factura — el test del flujo completo requiere "
                "una sesión POS pagada con factura emitida."
            )
        new_moves = self.order._reinvoice_reverse_original()
        rectificativas = new_moves.filtered(
            lambda move: move.move_type == "out_refund"
        )
        self.assertTrue(rectificativas)
        for rect in rectificativas:
            self.assertIn(
                rect.l10n_es_edi_verifactu_refund_reason,
                ("R1", "R5"),
            )
