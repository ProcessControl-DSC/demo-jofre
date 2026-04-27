from itertools import groupby

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _create_move_from_pos_order_lines(self, lines):
        if not lines.filtered("location_id"):
            return super()._create_move_from_pos_order_lines(lines)

        self.ensure_one()

        def get_grouping_key(line):
            loc_id = line.location_id.id or self.location_id.id
            return (
                line.product_id.id,
                tuple(sorted(line.attribute_value_ids.ids)),
                loc_id,
            )

        sorted_lines = sorted(lines, key=get_grouping_key)
        lines_by_group = groupby(sorted_lines, key=get_grouping_key)
        move_vals = []
        for _key, olines in lines_by_group:
            order_lines = self.env["pos.order.line"].concat(*olines)
            move_vals.append(
                self._prepare_stock_move_vals(order_lines[0], order_lines)
            )
        moves = self.env["stock.move"].create(move_vals)
        confirmed_moves = moves._action_confirm()
        confirmed_moves._add_mls_related_to_order(lines, are_qties_done=True)
        confirmed_moves.picked = True
        self._link_owner_on_return_picking(lines)

    def _prepare_stock_move_vals(self, first_line, order_lines):
        vals = super()._prepare_stock_move_vals(first_line, order_lines)
        chosen = first_line.location_id
        if not chosen:
            return vals
        chosen_path = chosen.parent_path or ""
        source = self.location_id
        dest = self.location_dest_id
        source_path = source.parent_path or ""
        dest_path = dest.parent_path or ""
        if source.usage == "internal" and source_path and chosen_path.startswith(source_path):
            # Outgoing flow: chosen location is the source of the move
            vals["location_id"] = chosen.id
        elif dest.usage == "internal" and dest_path and chosen_path.startswith(dest_path):
            # Incoming flow (refund): chosen location is the destination of the move
            vals["location_dest_id"] = chosen.id
        return vals
