from odoo import models


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_reinvoice_verifactu_refund_reason(self):
        """Código R1-R5 que corresponde a la rectificativa de la refacturación.

        R5 — factura rectificativa concerniente a una factura simplificada.
        R1 — Art. 80.1/80.2 LIVA y error de derecho (caso por defecto al
        cambiar el destinatario de una factura ya emitida)."""
        self.ensure_one()
        if (
            "is_l10n_es_simplified_invoice" in self._fields
            and self.is_l10n_es_simplified_invoice
        ):
            return "R5"
        return "R1"

    def _reinvoice_reverse_original(self):
        """Asigna la causa de rectificación R1/R5 en la rectificativa creada.

        El campo ``l10n_es_edi_verifactu_substituted_entry_id`` lo coloca
        automáticamente ``l10n_es_edi_verifactu`` en
        ``account.move.reversal._modify_default_reverse_values``,
        apuntando desde la rectificativa a la factura original — que es lo
        que espera Veri*Factu para construir el reporting
        ``correction_substitution`` (método "S - sustitución" AEAT)."""
        self.ensure_one()
        refund_reason = self._get_reinvoice_verifactu_refund_reason()
        new_moves = super()._reinvoice_reverse_original()
        if new_moves and refund_reason:
            rectificativas = new_moves.filtered(
                lambda move: (
                    move.move_type == "out_refund"
                    and "l10n_es_edi_verifactu_refund_reason" in move._fields
                )
            )
            if rectificativas:
                rectificativas.write({
                    "l10n_es_edi_verifactu_refund_reason": refund_reason,
                })
        return new_moves
