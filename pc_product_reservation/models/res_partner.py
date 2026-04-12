# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    reservation_count = fields.Integer(
        string='Reservas activas',
        compute='_compute_reservation_count',
    )

    def _compute_reservation_count(self):
        reservation_data = self.env['product.reservation']._read_group(
            domain=[
                ('partner_id', 'in', self.ids),
                ('state', 'in', ('draft', 'confirmed')),
            ],
            groupby=['partner_id'],
            aggregates=['__count'],
        )
        mapped_data = {partner.id: count for partner, count in reservation_data}
        for partner in self:
            partner.reservation_count = mapped_data.get(partner.id, 0)

    def action_open_reservations(self):
        """Open customer reservations."""
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Reservas de %(partner)s', partner=self.name),
            'res_model': 'product.reservation',
            'view_mode': 'list,form,kanban',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
        if self.reservation_count == 1:
            reservation = self.env['product.reservation'].search(
                [('partner_id', '=', self.id), ('state', 'in', ('draft', 'confirmed'))],
                limit=1,
            )
            if reservation:
                action['res_id'] = reservation.id
                action['view_mode'] = 'form'
                action['views'] = [(False, 'form')]
        return action
