from odoo import models, fields, _
import logging

_logger = logging.getLogger(__name__)


class CfBankResilienceRunner(models.TransientModel):
    _name = 'cf.bank.resilience.runner'
    _description = 'Bonifica conti bancari archiviati'

    result_text = fields.Text(string='Risultato', readonly=True)

    def action_run(self):
        """Run full bank resilience fix."""
        stats = self.env['res.partner.bank'].cf_bulk_resolve_archived_banks(dry_run=False)
        self.result_text = (
            f"Bonifica completata:\n"
            f"- Riassegnati: {stats['reassigned']}\n"
            f"- Riattivati: {stats['unarchived']}\n"
            f"- Nessuna azione: {stats['noop']}\n"
            f"- Errori: {len(stats['errors'])}"
        )
        if stats['errors']:
            self.result_text += "\n\nErrori:\n" + "\n".join(stats['errors'][:20])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.bank.resilience.runner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_dry_run(self):
        """Run dry-run only — no changes committed."""
        stats = self.env['res.partner.bank'].cf_bulk_resolve_archived_banks(dry_run=True)
        self.result_text = (
            f"DRY-RUN completato (nessuna modifica applicata):\n"
            f"- Da riassegnare: {stats['reassigned']}\n"
            f"- Da riattivare: {stats['unarchived']}\n"
            f"- Nessuna azione necessaria: {stats['noop']}\n"
            f"- Errori: {len(stats['errors'])}"
        )
        if stats['errors']:
            self.result_text += "\n\nErrori:\n" + "\n".join(stats['errors'][:20])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cf.bank.resilience.runner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
