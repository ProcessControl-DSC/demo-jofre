from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosReinvoiceL10nEs(TransactionCase):
    """Verifica que el glue resetea is_l10n_es_simplified_invoice."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Cliente Refactura ES"}
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
            "is_l10n_es_simplified_invoice": True,
        })

    def test_simplified_flag_field_exists(self):
        self.assertIn(
            "is_l10n_es_simplified_invoice",
            self.env["pos.order"]._fields,
        )

    def test_clear_localization_flags_resets_simplified(self):
        self.assertTrue(self.order.is_l10n_es_simplified_invoice)
        self.order._reinvoice_clear_localization_flags()
        self.assertFalse(self.order.is_l10n_es_simplified_invoice)
