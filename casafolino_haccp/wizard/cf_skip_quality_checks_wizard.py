# -*- coding: utf-8 -*-
from odoo import fields, models, _


class CfSkipQualityChecksWizard(models.TransientModel):
    _name = "cf.skip.quality.checks.wizard"
    _description = "Conferma salto controlli qualita produzione"

    production_id = fields.Many2one(
        "mrp.production",
        string="Ordine di produzione",
        required=True,
        readonly=True,
    )
    workorder_id = fields.Many2one(
        "mrp.workorder",
        string="Ordine di lavoro",
        readonly=True,
    )
    confirm_skip = fields.Boolean(
        "Salta i controlli qualita per questa produzione retroattiva",
        required=True,
    )
    note = fields.Text(
        "Motivo",
        required=True,
        default=lambda self: _(
            "Produzione retroattiva: controlli qualita verificati fuori dalla linea di produzione."
        ),
    )

    def action_confirm_skip(self):
        self.ensure_one()
        self.production_id.write({
            "cf_skip_quality_checks_retroactive": self.confirm_skip,
            "cf_skip_quality_checks_note": self.note,
        })
        self.production_id._cf_mark_quality_checks_skipped()
        ctx = dict(self.env.context, cf_skip_quality_confirmed=True)
        if self.workorder_id:
            return self.workorder_id.with_context(ctx).button_finish()
        return self.production_id.with_context(ctx).button_mark_done()
