import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration 7.5 → 7.6: SLA dashboard config params (idempotente)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    IrConfig = env['ir.config_parameter'].sudo()

    # ── 1. Config params SLA soglie ──
    _logger.info("[mail migration 7.6] Step 1: verifica config params SLA...")
    if not IrConfig.get_param('casafolino_mail.sla_warning_days'):
        IrConfig.set_param('casafolino_mail.sla_warning_days', '3')
        _logger.info("[mail migration 7.6] Config param sla_warning_days creato (default 3).")
    else:
        _logger.info("[mail migration 7.6] Config param sla_warning_days gia' presente, skip.")

    if not IrConfig.get_param('casafolino_mail.sla_critical_days'):
        IrConfig.set_param('casafolino_mail.sla_critical_days', '7')
        _logger.info("[mail migration 7.6] Config param sla_critical_days creato (default 7).")
    else:
        _logger.info("[mail migration 7.6] Config param sla_critical_days gia' presente, skip.")

    # ── 2. Ricrea la SQL view (idempotente via CREATE OR REPLACE) ──
    _logger.info("[mail migration 7.6] Step 2: ricrea SQL view sla_partner...")
    cr.execute("DROP VIEW IF EXISTS casafolino_mail_sla_partner CASCADE")
    _logger.info("[mail migration 7.6] View droppata, sara' ricreata da init().")

    # ── 3. Count partner in dashboard (dopo init) ──
    cr.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM res_partner p
        JOIN crm_lead l ON l.partner_id = p.id
            AND l.active = TRUE AND l.type = 'opportunity'
        JOIN crm_stage s ON s.id = l.stage_id AND s.is_won = FALSE
    """)
    count = cr.fetchone()[0]
    _logger.info("[mail migration 7.6] Partner con lead aperti (candidati SLA): %d", count)
