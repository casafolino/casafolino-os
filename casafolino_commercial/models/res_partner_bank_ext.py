from odoo import models, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResPartnerBankExt(models.Model):
    _inherit = 'res.partner.bank'

    def write(self, vals):
        if 'active' in vals and not vals['active'] and not self.env.context.get('force_archive'):
            # Check if any of these banks are referenced by open invoices
            banks_to_archive = self.filtered(lambda b: b.active)
            if banks_to_archive:
                moves = self.env['account.move'].search([
                    ('partner_bank_id', 'in', banks_to_archive.ids),
                    ('state', 'in', ('draft', 'posted')),
                    ('payment_state', 'in', ('not_paid', 'partial', 'in_payment')),
                ])
                if moves:
                    move_names = moves[:5].mapped('name')
                    extra = len(moves) - 5
                    names_str = ', '.join(n for n in move_names if n)
                    if extra > 0:
                        names_str += f' ...e altre {extra}'
                    raise ValidationError(_(
                        "Impossibile archiviare questo conto bancario: è referenziato "
                        "da %(count)s fatture aperte (%(names)s). "
                        "Risolvere prima le fatture collegate.",
                        count=len(moves),
                        names=names_str,
                    ))
        return super().write(vals)

    @api.model
    def cf_bulk_resolve_archived_banks(self, dry_run=False):
        """Scan open account.move with archived partner_bank_id and resolve."""
        _logger.info("CF Bank Resilience: avvio scansione%s...", " (DRY-RUN)" if dry_run else "")

        # Find moves with archived bank accounts using SQL for performance
        self.env.cr.execute("""
            SELECT am.id
            FROM account_move am
            JOIN res_partner_bank rpb ON rpb.id = am.partner_bank_id
            WHERE am.state IN ('draft', 'posted')
              AND am.payment_state IN ('not_paid', 'partial', 'in_payment')
              AND (rpb.active = FALSE OR rpb.active IS NULL)
        """)
        move_ids = [r[0] for r in self.env.cr.fetchall()]

        if not move_ids:
            _logger.info("CF Bank Resilience: nessuna fattura con bank archiviato trovata.")
            return {'reassigned': 0, 'unarchived': 0, 'noop': 0, 'errors': []}

        _logger.info("CF Bank Resilience: trovate %d fatture da risolvere.", len(move_ids))

        if dry_run:
            savepoint = f"cf_bank_resilience_dry_{self.env.cr.now()}"
            self.env.cr.execute(f"SAVEPOINT {savepoint}")

        moves = self.env['account.move'].browse(move_ids)
        stats = {'reassigned': 0, 'unarchived': 0, 'noop': 0, 'errors': []}

        for move in moves:
            try:
                result = move._cf_resolve_archived_bank()
                action = result.get('action', 'noop')
                stats[action] = stats.get(action, 0) + 1
            except Exception as e:
                _logger.error("CF Bank Resilience: errore su fattura %s: %s", move.name, e)
                stats['errors'].append(f"{move.name}: {e}")

        if dry_run:
            self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            _logger.info("CF Bank Resilience DRY-RUN: reassigned=%d, unarchived=%d, noop=%d, errors=%d",
                         stats['reassigned'], stats['unarchived'], stats['noop'], len(stats['errors']))
        else:
            _logger.info("CF Bank Resilience: reassigned=%d, unarchived=%d, noop=%d, errors=%d",
                         stats['reassigned'], stats['unarchived'], stats['noop'], len(stats['errors']))

        return stats
