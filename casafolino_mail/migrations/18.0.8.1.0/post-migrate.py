import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.11.0 → 18.0.8.1.0 (F3): Intelligence rebuild cron, flag sync crons, outbox cron."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()

    # ── 1. Add new columns if needed (Odoo handles this via ORM, but belt+suspenders) ──
    _logger.info("[mail F3] Starting F3 migration...")

    # ── 2. Intelligence Rebuild Cron (hourly) ──
    _create_cron(env, Cron, {
        'cron_name': 'CasaFolino: Intelligence Rebuild',
        'model_name': 'casafolino.partner.intelligence',
        'code': 'model._rebuild_top_partners(limit=500)',
        'interval_number': 1,
        'interval_type': 'hours',
    })

    # ── 3. Flag Sync Push Cron (every 5 min) ──
    _create_cron(env, Cron, {
        'cron_name': 'CasaFolino: IMAP Flag Push',
        'model_name': 'casafolino.mail.flag.sync',
        'code': 'model._cron_push_flags()',
        'interval_number': 5,
        'interval_type': 'minutes',
        'active': False,  # Disabled by default — enable via config param
    })

    # ── 4. Flag Sync Pull Cron (every 10 min) ──
    _create_cron(env, Cron, {
        'cron_name': 'CasaFolino: IMAP Flag Pull',
        'model_name': 'casafolino.mail.flag.sync',
        'code': 'model._cron_pull_flags()',
        'interval_number': 10,
        'interval_type': 'minutes',
        'active': False,  # Disabled by default
    })

    # ── 5. Outbox Process Cron (every 2 min) ──
    _create_cron(env, Cron, {
        'cron_name': 'CasaFolino: Outbox Process',
        'model_name': 'casafolino.mail.outbox',
        'code': 'model._cron_process_outbox()',
        'interval_number': 2,
        'interval_type': 'minutes',
    })

    # ── 6. Outbox Cleanup Cron (daily) ──
    _create_cron(env, Cron, {
        'cron_name': 'CasaFolino: Outbox Cleanup',
        'model_name': 'casafolino.mail.outbox',
        'code': 'model._cron_cleanup_old_outbox()',
        'interval_number': 1,
        'interval_type': 'days',
    })

    # ── 7. Config parameters for F3 features ──
    ICP = env['ir.config_parameter'].sudo()
    params = {
        'casafolino.mail.v3_sync_flags_enabled': 'False',
        'casafolino.mail.v3_nba_llm_fallback': 'True',
        'casafolino.mail.v3_intelligence_enabled': 'True',
    }
    for key, default in params.items():
        if not ICP.get_param(key):
            ICP.set_param(key, default)
            _logger.info("[mail F3] Config param %s = %s", key, default)

    # ── 8. Initial intelligence rebuild for top 200 partners ──
    try:
        Intelligence = env['casafolino.partner.intelligence']
        count = Intelligence._rebuild_top_partners(limit=200)
        _logger.info("[mail F3] Initial intelligence rebuild: %d partners", count)
    except Exception as e:
        _logger.warning("[mail F3] Initial rebuild skipped: %s", e)

    # ── 9. SQL indexes for new fields ──
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_msg_intent
        ON casafolino_mail_message (intent_detected)
        WHERE intent_detected IS NOT NULL
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_msg_imap_flags_synced
        ON casafolino_mail_message (imap_flags_synced)
        WHERE imap_flags_synced = false
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_intelligence_partner
        ON casafolino_partner_intelligence (partner_id)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_intelligence_hotness
        ON casafolino_partner_intelligence (hotness_score DESC)
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_outbox_state
        ON casafolino_mail_outbox (state)
        WHERE state = 'queued'
    """)
    _logger.info("[mail F3] SQL indexes created")

    _logger.info("[mail F3] Migration complete")


def _create_cron(env, Cron, spec):
    """Create cron job idempotently."""
    name = spec['cron_name']
    if Cron.search([('cron_name', 'ilike', name)]):
        _logger.info("[mail F3] Cron '%s' already exists, skip", name)
        return

    model_ref = 'casafolino_mail.model_%s' % spec['model_name'].replace('.', '_')
    try:
        model = env.ref(model_ref)
    except Exception:
        _logger.warning("[mail F3] Model ref %s not found, skip cron '%s'", model_ref, name)
        return

    server_action = env['ir.actions.server'].create({
        'name': '%s - Action' % name,
        'model_id': model.id,
        'state': 'code',
        'code': spec['code'],
    })
    Cron.create({
        'cron_name': name,
        'ir_actions_server_id': server_action.id,
        'interval_number': spec['interval_number'],
        'interval_type': spec['interval_type'],
        'active': spec.get('active', True),
        'user_id': env.ref('base.user_admin').id,
    })
    _logger.info("[mail F3] Cron '%s' created (every %d %s)",
                 name, spec['interval_number'], spec['interval_type'])
