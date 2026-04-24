import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Bug A fix: dedup crons, set Mail Sync V2 interval to 5 min, trigger immediate fetch."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    # active_test=False to also find crons disabled during deploy
    Cron = env['ir.cron'].sudo().with_context(active_test=False)

    # ── 1. Dedup Mail Sync V2 crons, update interval to 5 min ──
    all_sync = Cron.search([('cron_name', 'ilike', 'CasaFolino%Mail Sync V2%')])
    if all_sync:
        keep = all_sync[0]
        dupes = all_sync - keep
        if dupes:
            _logger.info(
                "[casafolino_mail] migrate: removing %d duplicate Mail Sync V2 crons: %s",
                len(dupes), dupes.ids,
            )
            dupes.unlink()
        if keep.interval_number != 5 or keep.interval_type != 'minutes':
            keep.write({'interval_number': 5, 'interval_type': 'minutes'})
            _logger.info("[casafolino_mail] migrate: cron %d interval → 5 min", keep.id)
    else:
        _logger.warning("[casafolino_mail] migrate: no Mail Sync V2 cron found")

    # ── 2. Dedup all other CasaFolino crons ──
    dedup_patterns = [
        'CasaFolino%Silent Partners%',
        'CasaFolino%AI Classify%',
        'CasaFolino%Body Fetch%',
        'CasaFolino%Auto-Attach%',
        'CasaFolino%Digest Mittenti%',
    ]
    for pattern in dedup_patterns:
        crons = Cron.search([('cron_name', 'ilike', pattern)])
        if len(crons) > 1:
            keep_c = crons[0]
            dupes_c = crons - keep_c
            _logger.info(
                "[casafolino_mail] migrate: removing %d duplicate '%s' crons: %s",
                len(dupes_c), pattern, dupes_c.ids,
            )
            dupes_c.unlink()

    # ── 3. Trigger immediate fetch for connected accounts ──
    _logger.info("[casafolino_mail] migrate: triggering immediate fetch")
    try:
        accounts = env['casafolino.mail.account'].sudo().search([
            ('state', '=', 'connected'),
        ])
        for acc in accounts:
            try:
                acc._fetch_emails()
            except Exception as e:
                _logger.warning(
                    "[casafolino_mail] migrate: fetch failed for %s: %s",
                    acc.name, e,
                )
        _logger.info(
            "[casafolino_mail] migrate: fetch done, %d accounts processed",
            len(accounts),
        )
    except Exception as e:
        _logger.error("[casafolino_mail] migrate: fetch block error: %s", e)
