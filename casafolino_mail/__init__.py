import logging
from datetime import timedelta

from odoo import fields

from . import models
from . import wizard
from . import controllers

_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    """Setup iniziale modulo Mail CRM V2."""
    Cron = env['ir.cron'].sudo().with_context(active_test=False)

    # ── 1. Elimina cron orfani del vecchio stack ──
    old_cron_names = [
        'CasaFolino: IMAP Sync',
        'CF Mail: Sync ogni 20 minuti',
        'CasaFolino: Fetch nuove email (Hub)',
        'CasaFolino: Cleanup email scartate',
        'Mail Hub: Scarica body email in coda',
        'Mail Hub: Pulizia email scartate (30gg)',
    ]
    old_crons = Cron.search([('cron_name', 'in', old_cron_names)])
    if old_crons:
        old_crons.unlink()

    # Disattiva anche per ID noti (80, 81) se ancora presenti
    for cron_id in [80, 81]:
        try:
            c = Cron.browse(cron_id)
            if c.exists():
                c.active = False
        except Exception:
            pass

    # ── 2. Crea/aggiorna unico cron V2 (intervallo 5 min) ──
    # NOTE: In Odoo 18 cron_name is a related field from ir.actions.server.name,
    # so we search with ilike to match both legacy and current naming.
    model = env.ref('casafolino_mail.model_casafolino_mail_account')
    all_sync_crons = Cron.search([('cron_name', 'ilike', 'CasaFolino%Mail Sync V2%')])
    if all_sync_crons:
        # Keep first (oldest), delete duplicates
        keep = all_sync_crons[0]
        dupes = all_sync_crons - keep
        if dupes:
            _logger.info(
                "[casafolino_mail] Removing %d duplicate Mail Sync V2 crons: %s",
                len(dupes), dupes.ids,
            )
            dupes.unlink()
        if keep.interval_number != 5 or keep.interval_type != 'minutes':
            keep.write({'interval_number': 5, 'interval_type': 'minutes'})
            _logger.info("[casafolino_mail] Cron %d interval updated to 5 minutes", keep.id)
    else:
        server_action = env['ir.actions.server'].create({
            'name': 'CasaFolino Mail Sync V2 - Action',
            'model_id': model.id,
            'state': 'code',
            'code': 'model._cron_fetch_all_accounts()',
        })
        Cron.create({
            'cron_name': 'CasaFolino Mail Sync V2 - Action',
            'ir_actions_server_id': server_action.id,
            'interval_number': 5,
            'interval_type': 'minutes',
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })

    # ── 2b. V13: No immediate fetch — cron pipeline handles it ──
    _logger.info("[casafolino_mail] Post-init: fetch deferred to cron pipeline (V13)")

    # ── 3. Seed sender_policy di esempio ──
    Policy = env['casafolino.mail.sender_policy'].sudo()
    if not Policy.search_count([]):
        Policy.create([
            {
                'name': 'Newsletter domain → discard',
                'pattern_type': 'domain',
                'pattern_value': '*mailup*',
                'action': 'auto_discard',
                'priority': 80,
            },
            {
                'name': 'REWE group → keep auto',
                'pattern_type': 'domain',
                'pattern_value': '*rewe-group*',
                'action': 'auto_keep',
                'priority': 50,
                'auto_create_partner': True,
            },
            {
                'name': 'Default: review',
                'pattern_type': 'domain',
                'pattern_value': '*',
                'action': 'review',
                'priority': 1,
            },
        ])

    # ── 4. Cron Silent Partners Alert (dedup + idempotent) ──
    all_silent_crons = Cron.search([('cron_name', 'ilike', 'CasaFolino%Silent Partners%')])
    if all_silent_crons:
        keep_silent = all_silent_crons[0]
        dupes_silent = all_silent_crons - keep_silent
        if dupes_silent:
            _logger.info(
                "[casafolino_mail] Removing %d duplicate Silent Partners crons: %s",
                len(dupes_silent), dupes_silent.ids,
            )
            dupes_silent.unlink()
    else:
        server_action_silent = env['ir.actions.server'].create({
            'name': 'CasaFolino Silent Partners - Action',
            'model_id': model.id,
            'state': 'code',
            'code': 'model._cron_silent_partners_alert()',
        })
        tomorrow_7am = fields.Datetime.now().replace(
            hour=7, minute=0, second=0) + timedelta(days=1)
        Cron.create({
            'cron_name': 'CasaFolino Silent Partners - Action',
            'ir_actions_server_id': server_action_silent.id,
            'interval_number': 1,
            'interval_type': 'days',
            'nextcall': tomorrow_7am,
            'active': True,
            'user_id': env.ref('base.user_admin').id,
        })

    # ── 4b. Create system folders for all accounts ──
    Folder = env['casafolino.mail.folder'].sudo()
    all_accounts = env['casafolino.mail.account'].sudo().search([])
    for acct in all_accounts:
        Folder._create_system_folders(acct.id)

    # ── 5. Config parameter: silent_days_threshold ──
    IrConfig = env['ir.config_parameter'].sudo()
    if not IrConfig.get_param('casafolino_mail.silent_days_threshold'):
        IrConfig.set_param('casafolino_mail.silent_days_threshold', '21')

    # ── 6. Cron Triage RAW (dedup + idempotent) ──
    raw_model = env.ref('casafolino_mail.model_casafolino_mail_raw')
    all_triage_crons = Cron.search([('cron_name', 'ilike', 'CasaFolino%Triage RAW%')])
    if all_triage_crons:
        keep_triage = all_triage_crons[0]
        dupes_triage = all_triage_crons - keep_triage
        if dupes_triage:
            _logger.info(
                "[casafolino_mail] Removing %d duplicate Triage RAW crons: %s",
                len(dupes_triage), dupes_triage.ids,
            )
            dupes_triage.unlink()
    else:
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

    # ── 7. Cron Cleanup RAW (dedup + idempotent) ──
    all_cleanup_crons = Cron.search([('cron_name', 'ilike', 'CasaFolino%Cleanup RAW%')])
    if all_cleanup_crons:
        keep_cleanup = all_cleanup_crons[0]
        dupes_cleanup = all_cleanup_crons - keep_cleanup
        if dupes_cleanup:
            _logger.info(
                "[casafolino_mail] Removing %d duplicate Cleanup RAW crons: %s",
                len(dupes_cleanup), dupes_cleanup.ids,
            )
            dupes_cleanup.unlink()
    else:
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
