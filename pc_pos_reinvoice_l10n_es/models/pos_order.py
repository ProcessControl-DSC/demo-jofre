from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _reinvoice_clear_localization_flags(self):
        """Reset del flag de simplificada para que, al regenerar la factura
        sobre el partner correcto, se emita una factura completa en el diario
        de facturación normal y no se vea forzada por el override de
        l10n_es_pos al diario de simplificadas."""
        super()._reinvoice_clear_localization_flags()
        if "is_l10n_es_simplified_invoice" in self._fields:
            self.is_l10n_es_simplified_invoice = False
