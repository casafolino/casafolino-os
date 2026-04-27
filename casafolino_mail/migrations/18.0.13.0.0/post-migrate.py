import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """V13 migration: DELETE CASCADE existing messages, reset fetch dates for backfill."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    ICP = env['ir.config_parameter'].sudo()

    # Always register crons and set default feature flag
    _register_v13_crons(env)

    # Set feature flag default (OFF = legacy behavior)
    if not ICP.get_param('casafolino.use_raw_pipeline'):
        ICP.set_param('casafolino.use_raw_pipeline', 'false')
        _logger.info("[V13 migrate] Set casafolino.use_raw_pipeline = false (default)")

    # Data migration (DELETE CASCADE) only runs when explicitly triggered
    # via SQL after flipping the feature flag. NOT automatic.
    _logger.info("[V13 migrate] Data migration deferred to manual flip. Feature flag OFF.")


def _register_v13_crons(env):
    """Register Triage RAW and Cleanup RAW crons if missing."""
    from datetime import timedelta
    from odoo import fields

    Cron = env['ir.cron'].sudo().with_context(active_test=False)

    try:
        raw_model = env['ir.model'].sudo().search([
            ('model', '=', 'casafolino.mail.raw')
        ], limit=1)
        if not raw_model:
            _logger.warning("[V13 migrate] casafolino.mail.raw model not found, skip cron creation")
            return
    except Exception:
        _logger.warning("[V13 migrate] Cannot find RAW model, skip cron creation")
        return

    # Triage RAW cron
    existing_triage = Cron.search([('cron_name', 'ilike', 'CasaFolino%Triage RAW%')])
    if not existing_triage:
        sa_triage = env['ir.actions.server'].create({
            'name': 'CasaFolino Triage RAW - Action',
            'model_id': raw_model.id,
            'state': 'code',
            'code': 'model._cron_triage_raw()',
        })
        Cron.create({
            'cron_name': 'CasaFolino Triage RAW - Action',
            'ir_actions_server_id': sa_triage.id,
            'interval_number': 5,
            'interval_type': 'minutes',
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[V13 migrate] Created Triage RAW cron")
    else:
        _logger.info("[V13 migrate] Triage RAW cron already exists (id=%d)", existing_triage[0].id)

    # Cleanup RAW cron
    existing_cleanup = Cron.search([('cron_name', 'ilike', 'CasaFolino%Cleanup RAW%')])
    if not existing_cleanup:
        sa_cleanup = env['ir.actions.server'].create({
            'name': 'CasaFolino Cleanup RAW - Action',
            'model_id': raw_model.id,
            'state': 'code',
            'code': 'model._cron_cleanup_raw()',
        })
        tomorrow_3am = fields.Datetime.now().replace(
            hour=3, minute=0, second=0) + timedelta(days=1)
        Cron.create({
            'cron_name': 'CasaFolino Cleanup RAW - Action',
            'ir_actions_server_id': sa_cleanup.id,
            'interval_number': 1,
            'interval_type': 'days',
            'nextcall': tomorrow_3am,
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })
        _logger.info("[V13 migrate] Created Cleanup RAW cron")
    else:
        _logger.info("[V13 migrate] Cleanup RAW cron already exists (id=%d)", existing_cleanup[0].id)
