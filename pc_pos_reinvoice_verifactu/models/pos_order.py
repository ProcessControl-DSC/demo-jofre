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

        El wizard nativo ``account.move.reversal`` de
        ``l10n_es_edi_verifactu`` solo aplica ``_modify_default_reverse_values``
        cuando se invoca vía ``modify_moves()`` (is_modify=True). Aquí usamos
        ``refund_moves()`` (is_modify=False), así que asignamos el
        refund_reason manualmente en la rectificativa generada."""
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

    def _reinvoice_generate_new_invoice(self, old_move=None):
        """Marca la nueva factura como sustituta de la original para Veri*Factu.

        ``l10n_es_edi_verifactu_substituted_entry_id`` va en la nueva
        factura ``out_invoice`` apuntando a la factura original. Lo
        construye nativo ``account.move.reversal._modify_default_reverse_values``
        cuando se ejecuta el flujo ``modify_moves()``, pero aquí seguimos
        un flujo manual (rectificativa + nueva factura por separado), así
        que asignamos el campo a mano usando ``old_move`` recibido del
        flujo principal de refacturación."""
        self.ensure_one()
        new_invoice = super()._reinvoice_generate_new_invoice(old_move=old_move)
        if (
            old_move
            and "l10n_es_edi_verifactu_substituted_entry_id"
            in new_invoice._fields
        ):
            new_invoice.l10n_es_edi_verifactu_substituted_entry_id = old_move
        return new_invoice
