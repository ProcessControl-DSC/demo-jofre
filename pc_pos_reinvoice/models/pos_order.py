from odoo import _, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    re_invoiced = fields.Boolean(
        string="Refacturado",
        default=False,
        copy=False,
        readonly=True,
        help="Marca si este pedido ha sido refacturado a otro cliente "
             "desde el TPV, generando una rectificativa y una nueva factura.",
    )
    reinvoice_ids = fields.Many2many(
        comodel_name="account.move",
        relation="pos_order_reinvoice_move_rel",
        column1="order_id",
        column2="move_id",
        string="Histórico de facturas",
        copy=False,
        readonly=True,
        help="Factura original, rectificativa y nueva factura "
             "tras la refacturación.",
    )

    def action_pos_reinvoice(self, partner_id):
        """Entry point invocado desde el TPV para refacturar el pedido."""
        self.ensure_one()
        self._check_reinvoice_allowed(partner_id)
        return self._do_reinvoice(partner_id)

    def _check_reinvoice_allowed(self, new_partner_id):
        self.ensure_one()
        if not self.config_id.allow_reinvoice:
            raise UserError(_(
                "La refacturación no está habilitada en este TPV. "
                "Actívala en la configuración del punto de venta."
            ))
        if self.re_invoiced:
            raise UserError(_("Este pedido ya ha sido refacturado."))
        if self.refund_orders_count:
            raise UserError(_(
                "No se puede refacturar un pedido con devoluciones asociadas. "
                "Hazlo manualmente desde Contabilidad."
            ))
        if not new_partner_id:
            raise UserError(_("Selecciona un cliente para la refacturación."))
        if self.partner_id.id == new_partner_id:
            raise UserError(_("El nuevo cliente debe ser distinto del actual."))
        if (
            self.session_id.state in ("closing_control", "closed")
            and not self.config_id.allow_reinvoice_closed_session
        ):
            raise UserError(_(
                "La sesión POS está cerrada. Activa el permiso de "
                "refacturación post-cierre en la configuración del TPV "
                "o reabre la sesión."
            ))
        return True

    def _do_reinvoice(self, new_partner_id):
        self.ensure_one()
        old_partner = self.partner_id
        old_move = self.account_move
        new_partner = self.env["res.partner"].browse(new_partner_id)
        payment_lines = self._reinvoice_break_reconciliation()
        self._reinvoice_reverse_original()
        self.write({"partner_id": new_partner.id})
        self.account_move = False
        self._reinvoice_clear_localization_flags()
        new_invoice = self._reinvoice_generate_new_invoice(old_move=old_move)
        self._reinvoice_reassign_payments(
            payment_lines, new_partner, new_invoice
        )
        self.re_invoiced = True
        self._reinvoice_post_audit(old_partner, new_partner, new_invoice)
        return new_invoice.id

    def _reinvoice_break_reconciliation(self):
        """Localiza apuntes de cobro reconciliados, rompe la reconciliación
        y devuelve los apuntes de pago para reasignarlos al nuevo cliente."""
        self.ensure_one()
        if not self.account_move:
            return self.env["account.move.line"]
        receivable_lines = self.account_move.line_ids.filtered(
            lambda line: (
                line.account_id.account_type == "asset_receivable"
                or line.account_id == self.company_id.transfer_account_id
            )
        )
        partials = self.env["account.partial.reconcile"].search([
            "|",
            ("debit_move_id", "in", receivable_lines.ids),
            ("credit_move_id", "in", receivable_lines.ids),
        ])
        invoice_line_ids = set(self.account_move.line_ids.ids)
        payment_lines = self.env["account.move.line"]
        for partial in partials:
            for side in (partial.debit_move_id, partial.credit_move_id):
                if side.id not in invoice_line_ids:
                    payment_lines |= side
        if partials:
            self.account_move.js_remove_outstanding_partial(partials.ids)
        return payment_lines

    def _reinvoice_reverse_original(self):
        """Crea y postea la rectificativa de la factura original.
        Almacena original y rectificativa en reinvoice_ids.

        Si el módulo l10n_es_edi_verifactu está instalado, escribe en la
        rectificativa la causa de rectificación R1/R5 a partir de
        ``_get_reinvoice_verifactu_refund_reason``."""
        self.ensure_one()
        if not self.account_move:
            return self.env["account.move"]
        original = self.account_move
        wizard = self.env["account.move.reversal"].with_context(
            active_ids=original.ids,
            active_model="account.move",
        ).create({
            "reason": _("Refacturación POS"),
            "journal_id": original.journal_id.id,
        })
        wizard.refund_moves()
        new_moves = wizard.new_move_ids
        draft = new_moves.filtered(lambda move: move.state == "draft")
        if draft:
            draft.sudo().with_company(self.company_id)._post(soft=False)
        self.reinvoice_ids = [(4, original.id)] + [
            (4, move.id) for move in new_moves
        ]
        refund_reason = self._get_reinvoice_verifactu_refund_reason()
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

    def _reinvoice_clear_localization_flags(self):
        """Resetea flags de localización antes de regenerar la nueva factura.

        Si el módulo l10n_es_pos está instalado, desmarca
        ``is_l10n_es_simplified_invoice`` para que la nueva factura sea
        ordinaria y vaya al diario normal, no al de simplificadas."""
        self.ensure_one()
        if "is_l10n_es_simplified_invoice" in self._fields:
            self.is_l10n_es_simplified_invoice = False

    def _reinvoice_generate_new_invoice(self, old_move=None):
        """Genera la nueva factura sin pasar por el wrapper
        _generate_pos_order_invoice (que duplicaría apuntes de pago).
        Replicamos solo _create_invoice + _post.

        Si el módulo l10n_es_edi_verifactu está instalado y se nos pasó
        ``old_move``, escribe ``l10n_es_edi_verifactu_substituted_entry_id``
        en la nueva factura apuntando a ``old_move`` para que Veri*Factu
        reporte la sustitución correctamente."""
        self.ensure_one()
        company = self.company_id
        invoice_vals = self._prepare_invoice_vals()
        invoice = self._create_invoice(invoice_vals)
        invoice.sudo().with_company(company).with_context(
            **self._get_invoice_post_context()
        )._post()
        self.account_move = invoice
        self.reinvoice_ids = [(4, invoice.id)]
        if (
            old_move
            and "l10n_es_edi_verifactu_substituted_entry_id"
            in invoice._fields
        ):
            invoice.l10n_es_edi_verifactu_substituted_entry_id = old_move
        return invoice

    def _reinvoice_reassign_payments(
        self, payment_lines, new_partner, new_invoice
    ):
        """Reasigna el partner en los apuntes de pago y los reconcilia
        con la cuenta a cobrar de la nueva factura."""
        self.ensure_one()
        if not payment_lines:
            return
        payment_lines.write({"partner_id": new_partner.id})
        receivable_lines = new_invoice.line_ids.filtered(
            lambda line: (
                line.account_id.account_type == "asset_receivable"
                and not line.reconciled
            )
        )
        if receivable_lines:
            (payment_lines | receivable_lines).reconcile()

    def _reinvoice_post_audit(self, old_partner, new_partner, new_invoice):
        """Mensaje en chatter del pos.order para trazabilidad."""
        self.ensure_one()
        self.message_post(body=_(
            "Pedido refacturado. Cliente: %(old)s → %(new)s. "
            "Nueva factura: %(inv)s.",
            old=old_partner.display_name,
            new=new_partner.display_name,
            inv=new_invoice.display_name,
        ))

    def _get_reinvoice_verifactu_refund_reason(self):
        """Código R1-R5 que corresponde a la rectificativa de la refacturación.

        R5 — factura rectificativa concerniente a una factura simplificada.
        R1 — Art. 80.1/80.2 LIVA y error de derecho (caso por defecto al
        cambiar el destinatario de una factura ordinaria ya emitida).

        Devuelve ``False`` si ``l10n_es_edi_verifactu`` no está instalado
        o si ``l10n_es_pos`` no aporta el flag de simplificada."""
        self.ensure_one()
        if "l10n_es_edi_verifactu_refund_reason" not in self.env[
            "account.move"
        ]._fields:
            return False
        if (
            "is_l10n_es_simplified_invoice" in self._fields
            and self.is_l10n_es_simplified_invoice
        ):
            return "R5"
        return "R1"

    def action_view_invoice(self):
        action = super().action_view_invoice()
        if self.reinvoice_ids:
            action.update({
                "view_mode": "list,form",
                "domain": [("id", "in", self.reinvoice_ids.ids)],
                "name": _("Histórico de facturas"),
            })
            action.pop("res_id", None)
            action.pop("view_id", None)
        return action
