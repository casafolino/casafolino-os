# -*- coding: utf-8 -*-
import datetime

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    @api.depends("product_id")
    def _compute_expiration_date(self):
        for lot in self:
            if lot.expiration_date:
                continue
            duration = lot.product_id.use_expiration_date and lot.product_id.expiration_time
            lot.expiration_date = (
                datetime.datetime.now() + datetime.timedelta(days=duration)
                if duration
                else False
            )


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.depends("product_id", "lot_id.expiration_date", "picking_id.scheduled_date")
    def _compute_expiration_date(self):
        for move_line in self:
            if move_line.lot_id.expiration_date:
                move_line.expiration_date = move_line.lot_id.expiration_date
            elif move_line.picking_type_use_create_lots and move_line.product_id.use_expiration_date:
                duration = move_line.product_id.expiration_time
                if duration and not move_line.expiration_date:
                    from_date = move_line.picking_id.scheduled_date or fields.Datetime.today()
                    move_line.expiration_date = from_date + datetime.timedelta(days=duration)
                elif not duration:
                    move_line.expiration_date = move_line.expiration_date or False
            else:
                move_line.expiration_date = False

    @api.onchange("product_id", "product_uom_id", "picking_id")
    def _onchange_product_id(self):
        res = super()._onchange_product_id()
        if not self.picking_type_use_create_lots:
            return res
        if not self.product_id.use_expiration_date:
            self.expiration_date = False
            return res
        duration = self.product_id.expiration_time
        if duration:
            from_date = self.picking_id.scheduled_date or fields.Datetime.today()
            self.expiration_date = from_date + datetime.timedelta(days=duration)
        else:
            self.expiration_date = False
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    def _generate_serial_move_line_commands(self, field_data, location_dest_id=False, origin_move_line=None):
        commands = super()._generate_serial_move_line_commands(field_data, location_dest_id, origin_move_line)
        if not self.product_id.use_expiration_date or self.product_id.expiration_time:
            return commands

        for index, command in enumerate(commands):
            if len(command) < 3:
                continue
            source_data = field_data[index] if index < len(field_data) else {}
            manual_expiration = source_data.get("expiration_date") or source_data.get("datetime")
            if not manual_expiration:
                command[2].pop("expiration_date", None)
        return commands
