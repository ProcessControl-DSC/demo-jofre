import math

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StoreDistributionProfile(models.Model):
    _name = 'store.distribution.profile'
    _description = 'Perfil de distribución por tienda'
    _order = 'name'

    name = fields.Char(required=True)
    line_ids = fields.One2many('store.distribution.profile.line', 'profile_id', string='Tiendas')
    total_percentage = fields.Float(compute='_compute_total_percentage')
    active = fields.Boolean(default=True)

    @api.depends('line_ids.percentage')
    def _compute_total_percentage(self):
        for rec in self:
            rec.total_percentage = sum(rec.line_ids.mapped('percentage'))

    @api.constrains('line_ids')
    def _check_percentage_sum(self):
        for rec in self:
            total = sum(rec.line_ids.mapped('percentage'))
            if rec.line_ids and abs(total - 100.0) > 0.01:
                raise ValidationError(
                    f"Los porcentajes deben sumar 100%%. Actualmente suman {total:.1f}%%."
                )

    def distribute_hund(self, total_qty):
        """Distribuye total_qty entre tiendas usando el método de Hund (largest remainder).

        :param int total_qty: cantidad total a distribuir
        :return: lista de dicts {warehouse_id: id, qty: int}
        """
        self.ensure_one()
        if not self.line_ids or total_qty <= 0:
            return []

        allocations = []
        for line in self.line_ids:
            raw = total_qty * line.percentage / 100.0
            allocations.append({
                'warehouse_id': line.warehouse_id.id,
                'warehouse_name': line.warehouse_id.name,
                'raw': raw,
                'floor': math.floor(raw),
                'remainder': raw - math.floor(raw),
            })

        distributed = sum(a['floor'] for a in allocations)
        leftover = total_qty - distributed

        # Asignar unidades restantes por mayor fracción decimal (método de Hund)
        allocations.sort(key=lambda a: a['remainder'], reverse=True)
        for i in range(int(leftover)):
            allocations[i]['floor'] += 1

        return [
            {'warehouse_id': a['warehouse_id'], 'warehouse_name': a['warehouse_name'], 'qty': a['floor']}
            for a in allocations
            if a['floor'] > 0
        ]


class StoreDistributionProfileLine(models.Model):
    _name = 'store.distribution.profile.line'
    _description = 'Línea de perfil de distribución'
    _order = 'sequence, id'

    profile_id = fields.Many2one('store.distribution.profile', required=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', required=True, string='Tienda/Almacén')
    percentage = fields.Float(required=True, string='Porcentaje (%)')
    sequence = fields.Integer(default=10)
