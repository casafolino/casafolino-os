import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    _logger.info("[mail migration 8.0.0] Starting V3 F2 post-migrate")

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Step 1: Backfill thread_id per email keep esistenti
    _logger.info("[mail migration 8.0.0] Step 1: Backfill threads...")
    cr.execute("""
        SELECT id FROM casafolino_mail_message
        WHERE state IN ('keep', 'auto_keep') AND thread_id IS NULL
        ORDER BY email_date ASC
    """)
    message_ids = [r[0] for r in cr.fetchall()]
    total = len(message_ids)
    _logger.info("[mail migration 8.0.0] Found %d messages to backfill", total)

    Thread = env['casafolino.mail.thread']
    Message = env['casafolino.mail.message']
    chunk = 500
    for i in range(0, total, chunk):
        batch = message_ids[i:i + chunk]
        for mid in batch:
            try:
                msg = Message.browse(mid)
                if msg.exists():
                    Thread._upsert_from_message(msg)
            except Exception as e:
                _logger.warning("[mail migration 8.0.0] Thread upsert fail msg %s: %s", mid, e)
        cr.commit()
        _logger.info("[mail migration 8.0.0] Progress: %s/%s", min(i + chunk, total), total)

    # Step 2: Initial Intelligence rebuild for top partners
    _logger.info("[mail migration 8.0.0] Step 2: Intelligence initial rebuild")
    try:
        env['casafolino.partner.intelligence']._rebuild_top_partners(limit=500)
    except Exception as e:
        _logger.error("[mail migration 8.0.0] Intelligence rebuild fail: %s", e)

    # Step 3: Create cron 88 Draft Cleanup
    _logger.info("[mail migration 8.0.0] Step 3: Ensure cron Draft Cleanup")
    _ensure_cron(env,
                 name='CasaFolino: Draft Autosave Cleanup',
                 model='casafolino.mail.draft',
                 code='model._cron_cleanup_old_drafts()',
                 interval_number=1, interval_type='days')

    # Step 4: Create cron 90 Intelligence Rebuild
    _logger.info("[mail migration 8.0.0] Step 4: Ensure cron Intelligence Rebuild")
    _ensure_cron(env,
                 name='CasaFolino: Intelligence Rebuild',
                 model='casafolino.partner.intelligence',
                 code='model._rebuild_top_partners(limit=500)',
                 interval_number=1, interval_type='hours')

    # Step 5: Add Josefina, Martina to group_mail_v3_beta
    _logger.info("[mail migration 8.0.0] Step 5: Add beta users")
    beta_group = env.ref('casafolino_mail.group_mail_v3_beta', raise_if_not_found=False)
    if beta_group:
        for login_email in ['josefina.lazzaro@casafolino.com', 'martina.sinopoli@casafolino.com']:
            user = env['res.users'].search([('login', '=', login_email)], limit=1)
            if not user:
                user = env['res.users'].search([('email', 'ilike', login_email)], limit=1)
            if user:
                user.write({'groups_id': [(4, beta_group.id)]})
                _logger.info("[mail migration 8.0.0] Added %s to beta", login_email)
            else:
                _logger.warning("[mail migration 8.0.0] User %s not found", login_email)

    # Step 6: Create SQL indexes for V3
    _logger.info("[mail migration 8.0.0] Step 6: Create V3 indexes")
    indexes = [
        """CREATE INDEX IF NOT EXISTS idx_msg_thread
           ON casafolino_mail_message(thread_id, email_date DESC)""",
        """CREATE INDEX IF NOT EXISTS idx_msg_read
           ON casafolino_mail_message(is_read, account_id)
           WHERE state='keep'""",
        """CREATE INDEX IF NOT EXISTS idx_msg_partner_date
           ON casafolino_mail_message(partner_id, email_date DESC)
           WHERE state='keep'""",
        """CREATE INDEX IF NOT EXISTS idx_thread_account_date
           ON casafolino_mail_thread(account_id, last_message_date DESC)""",
        """CREATE INDEX IF NOT EXISTS idx_intelligence_hotness
           ON casafolino_partner_intelligence(hotness_score DESC)""",
    ]
    for idx_sql in indexes:
        try:
            cr.execute(idx_sql)
        except Exception as e:
            _logger.warning("[mail migration 8.0.0] Index creation: %s", e)

    cr.commit()
    _logger.info("[mail migration 8.0.0] Completed.")


def _ensure_cron(env, name, model, code, interval_number, interval_type):
    Cron = env['ir.cron'].sudo()
    existing = Cron.search([('cron_name', 'ilike', name)], limit=1)
    if existing:
        _logger.info("[mail migration 8.0.0] Cron '%s' already exists (id=%s)", name, existing.id)
        return existing

    model_rec = env['ir.model'].search([('model', '=', model)], limit=1)
    if not model_rec:
        _logger.error("[mail migration 8.0.0] Model %s not found, skip cron '%s'", model, name)
        return None

    server_action = env['ir.actions.server'].create({
        'name': name + ' - Action',
        'model_id': model_rec.id,
        'state': 'code',
        'code': code,
    })

    cron = Cron.create({
        'cron_name': name,
        'ir_actions_server_id': server_action.id,
        'interval_number': interval_number,
        'interval_type': interval_type,
        'active': True,
        'user_id': env.ref('base.user_admin').id,
    })
    _logger.info("[mail migration 8.0.0] Created cron '%s' (id=%s)", name, cron.id)
    return cron
