import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration → 11.0.0 (Personal Triage v11).

    1. Disable non-core crons (92, 93, 95, 96, 97)
    2. Ensure cron 82 (Sync V2) + 94 (Auto-attach) active
    3. Create "Digest Mittenti Fuori-CRM" cron (weekly)
    4. Create "Auto-Attach Leads" cron if not exists
    5. Add email_domains_extra column if not exists
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Cron = env['ir.cron'].sudo()

    _logger.info("[mail migration 11.0.0] Starting Personal Triage migration...")

    # ── 1. Disable non-core crons by name pattern ──
    non_core_names = [
        'Snooze', 'Scheduled Send', 'Follow-up',
        'Policy Backfill', 'AI Classification',
    ]
    for pattern in non_core_names:
        crons = Cron.search([
            ('cron_name', 'ilike', pattern),
            ('active', '=', True),
        ])
        for c in crons:
            c.active = False
            _logger.info("[mail 11.0.0] Disabled cron: %s (id=%d)", c.cron_name, c.id)

    # Also disable by known IDs if they exist
    cr.execute("""
        UPDATE ir_cron SET active = false
        WHERE id IN (92, 93, 95, 96, 97) AND active = true
    """)
    disabled = cr.rowcount
    if disabled:
        _logger.info("[mail 11.0.0] Disabled %d crons by ID (92,93,95,96,97)", disabled)

    # ── 2. Ensure core crons active ──
    cr.execute("""
        UPDATE ir_cron SET active = true
        WHERE id IN (82, 94) AND active = false
    """)

    # ── 3. Create Auto-Attach Leads cron ──
    cron_attach_name = 'CasaFolino: Auto-Attach Email a Lead'
    if not Cron.search([('cron_name', '=', cron_attach_name)]):
        model = env.ref('casafolino_mail.model_casafolino_mail_message', raise_if_not_found=False)
        if model:
            sa = env['ir.actions.server'].create({
                'name': cron_attach_name + ' - Action',
                'model_id': model.id,
                'state': 'code',
                'code': 'model._cron_auto_attach_leads()',
            })
            Cron.create({
                'cron_name': cron_attach_name,
                'ir_actions_server_id': sa.id,
                'interval_number': 15,
                'interval_type': 'minutes',
                'active': True,
                'user_id': env.ref('base.user_admin').id,
            })
            _logger.info("[mail 11.0.0] Created cron: %s (15 min)", cron_attach_name)

    # ── 4. Create Digest Fuori-CRM cron ──
    cron_digest_name = 'CasaFolino: Digest Mittenti Fuori-CRM'
    if not Cron.search([('cron_name', '=', cron_digest_name)]):
        model = env.ref('casafolino_mail.model_casafolino_mail_message', raise_if_not_found=False)
        if model:
            sa = env['ir.actions.server'].create({
                'name': cron_digest_name + ' - Action',
                'model_id': model.id,
                'state': 'code',
                'code': 'model._cron_digest_fuori_crm()',
            })
            Cron.create({
                'cron_name': cron_digest_name,
                'ir_actions_server_id': sa.id,
                'interval_number': 1,
                'interval_type': 'weeks',
                'active': True,
                'user_id': env.ref('base.user_admin').id,
                'nextcall': '2026-04-27 06:00:00',  # First Sunday after deploy
            })
            _logger.info("[mail 11.0.0] Created cron: %s (weekly)", cron_digest_name)

    # ── 5. Add email_domains_extra column ──
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'res_partner' AND column_name = 'email_domains_extra'
    """)
    if not cr.fetchone():
        cr.execute("ALTER TABLE res_partner ADD COLUMN email_domains_extra VARCHAR")
        _logger.info("[mail 11.0.0] Added column res_partner.email_domains_extra")

    _logger.info("[mail migration 11.0.0] Migration complete.")
