from . import models
from . import wizards

import logging
_logger = logging.getLogger(__name__)


def _post_init_bank_resilience(env):
    """Create daily cron and run one-shot bank resilience fix."""
    # Create cron if not exists
    cron = env['ir.cron'].search([
        ('cron_name', '=', 'CF: Bonifica bank account archiviati'),
    ], limit=1)
    if not cron:
        env['ir.cron'].create({
            'cron_name': 'CF: Bonifica bank account archiviati',
            'model_id': env.ref('base.model_res_partner_bank').id,
            'state': 'code',
            'code': 'model.cf_bulk_resolve_archived_banks()',
            'interval_number': 1,
            'interval_type': 'days',
            'active': True,
        })
        _logger.info("CF Bank Resilience: cron giornaliero creato.")

    # One-shot: resolve all archived banks on open invoices
    _logger.info("CF Bank Resilience: esecuzione one-shot al deploy...")
    stats = env['res.partner.bank'].cf_bulk_resolve_archived_banks(dry_run=False)
    _logger.info("CF Bank Resilience: one-shot completato — %s", stats)
