"""F6.5 migration: cron 96 backfill + @casafolino.com policy seed + lead rule internal domain field."""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _ensure_cron(env, name, model, code, interval_number, interval_type):
    """Create cron via ORM if not already present (idempotent)."""
    Cron = env['ir.cron'].sudo()
    existing = Cron.search([('cron_name', 'ilike', name)], limit=1)
    if existing:
        _logger.info("[mail v3 F6.5] Cron '%s' already exists (id=%s)", name, existing.id)
        return existing

    model_rec = env['ir.model'].search([('model', '=', model)], limit=1)
    if not model_rec:
        _logger.error("[mail v3 F6.5] Model %s not found, skip cron '%s'", model, name)
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
    _logger.info("[mail v3 F6.5] Created cron '%s' (id=%s)", name, cron.id)
    return cron


def _seed_casafolino_policy(env):
    """Seed @casafolino.com auto_keep policy (high priority) to exclude internal email from triage."""
    Policy = env['casafolino.mail.sender_policy'].sudo()
    existing = Policy.search([
        ('pattern_value', 'ilike', '@casafolino.com'),
        ('action', '=', 'auto_keep'),
    ], limit=1)
    if existing:
        _logger.info("[mail v3 F6.5] @casafolino.com policy already exists (id=%s)", existing.id)
        return existing

    policy = Policy.create({
        'name': 'Interni: @casafolino.com auto-keep',
        'pattern_type': 'domain',
        'pattern_value': '*@casafolino.com*',
        'action': 'auto_keep',
        'priority': 90,
        'notes': 'Email interne CasaFolino — escluse dal triage. Seed F6.5.',
    })
    _logger.info("[mail v3 F6.5] Created @casafolino.com auto_keep policy (id=%s)", policy.id)

    # Retroactive: update existing new/review inbound from @casafolino.com
    Msg = env['casafolino.mail.message'].sudo()
    msgs = Msg.search([
        ('state', 'in', ['new', 'review']),
        ('direction', '=', 'inbound'),
        ('sender_domain', '=ilike', 'casafolino.com'),
    ])
    if msgs:
        msgs.write({'state': 'auto_keep', 'policy_applied_id': policy.id})
        _logger.info("[mail v3 F6.5] Retroactive @casafolino.com: %d messages -> auto_keep", len(msgs))

    return policy


def _backfill_exclude_internal_domains(cr):
    """Set default exclude_internal_domains on existing lead rules."""
    cr.execute("""
        ALTER TABLE casafolino_mail_lead_rule
        ADD COLUMN IF NOT EXISTS exclude_internal_domains VARCHAR;
    """)
    cr.execute("""
        UPDATE casafolino_mail_lead_rule
        SET exclude_internal_domains = 'casafolino.com,casafolino.it'
        WHERE exclude_internal_domains IS NULL;
    """)


def migrate(cr, version):
    _logger.info('[mail v3 F6.5] Starting migration 18.0.8.5.1')
    env = api.Environment(cr, SUPERUSER_ID, {})

    # ── 1. Cron 96: Policy Backfill (every 6 hours) ──
    _ensure_cron(env,
                 name='Mail V3: Policy Backfill',
                 model='casafolino.mail.sender_policy',
                 code='model._cron_backfill_policies()',
                 interval_number=6, interval_type='hours')

    # ── 2. Seed @casafolino.com policy ──
    _seed_casafolino_policy(env)

    # ── 3. Add exclude_internal_domains field to lead rules ──
    _backfill_exclude_internal_domains(cr)

    _logger.info('[mail v3 F6.5] Migration 18.0.8.5.1 complete')
