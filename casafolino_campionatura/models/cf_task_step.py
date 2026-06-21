from odoo import models, _
from odoo.exceptions import UserError


class CfTaskStep(models.Model):
    """Hook ADDITIVO sul motore cf.task: le conferme degli step di una
    campionatura fanno avanzare la cf.shipment collegata. Nessuna modifica
    al core di cf.task (solo override con super())."""
    _inherit = 'cf.task.step'

    def _campionatura_shipment(self):
        self.ensure_one()
        if self.task_id.template_key != 'campionatura':
            return self.env['cf.shipment']
        return self.env['cf.shipment'].search(
            [('task_id', '=', self.task_id.id)], limit=1)

    def action_confirm(self):
        # Pre-check logistica: tracking obbligatorio PRIMA di confermare/spedire.
        for step in self:
            if step.task_id.template_key == 'campionatura' and step.role == 'logistica':
                shipment = step._campionatura_shipment()
                if shipment and (not shipment.tracking_code or not shipment.carrier):
                    raise UserError(_(
                        "Logistica: inserisci corriere e tracking sulla spedizione "
                        "prima di confermare lo step."))
        res = super().action_confirm()
        for step in self:
            shipment = step._campionatura_shipment()
            if not shipment:
                continue
            if step.role == 'creazione' and shipment.state in ('creato', 'preparazione'):
                if shipment.state == 'creato':
                    shipment.action_set_preparazione()
            elif step.role == 'logistica' and shipment.state not in ('spedito', 'consegnato'):
                shipment.action_set_spedito()
        return res
