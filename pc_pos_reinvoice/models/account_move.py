from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    pc_reinvoice_related_ids = fields.Many2many(
        comodel_name="account.move",
        relation="pc_reinvoice_account_move_related_rel",
        column1="move_id",
        column2="related_move_id",
        compute="_compute_pc_reinvoice_related",
        string="Facturas relacionadas (refacturación POS)",
        help="Facturas vinculadas a este apunte por una refacturación POS "
             "(la original, la rectificativa y la nueva factura sustitutiva).",
    )
    pc_reinvoice_related_count = fields.Integer(
        compute="_compute_pc_reinvoice_related",
        string="Nº facturas relacionadas",
    )
    pc_reinvoice_role = fields.Char(
        compute="_compute_pc_reinvoice_related",
        string="Rol en la refacturación",
        help="Indica el papel de esta factura dentro de la refacturación POS: "
             "original, rectificativa o sustitutiva.",
    )

    @api.depends()
    def _compute_pc_reinvoice_related(self):
        for move in self:
            pos_orders = self.env["pos.order"].search([
                ("reinvoice_ids", "in", move.id),
            ])
            related = pos_orders.reinvoice_ids.filtered(
                lambda m: m.id != move.id
            )
            move.pc_reinvoice_related_ids = related
            move.pc_reinvoice_related_count = len(related)
            move.pc_reinvoice_role = move._pc_reinvoice_role_label(pos_orders)

    def _pc_reinvoice_role_label(self, pos_orders):
        """Etiqueta el rol de este move dentro del trío de refacturación.

        - ``original``: factura inicial rectificada.
        - ``rectificativa``: rectificativa creada al refacturar.
        - ``sustitutiva``: nueva factura emitida al cliente correcto.
        - vacío si no participa en ninguna refacturación POS."""
        self.ensure_one()
        if not pos_orders:
            return ""
        if self.move_type == "out_refund":
            return _("Rectificativa")
        first_order = pos_orders.sorted("id")[:1]
        if first_order and first_order.account_move == self:
            return _("Nueva factura sustitutiva")
        return _("Factura original")

    def action_view_pc_reinvoice_related(self):
        self.ensure_one()
        related = self.pc_reinvoice_related_ids | self
        return {
            "type": "ir.actions.act_window",
            "name": _("Refacturación POS"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", related.ids)],
            "context": {"create": False},
        }
