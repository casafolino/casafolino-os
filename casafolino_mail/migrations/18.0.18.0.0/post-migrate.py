"""Brief #6.0 Phase 4 — Cleanup colonne orfane post-demolizione.

Sender policy engine, triage wizard, legacy fetch path demolished.
Columns and tables orphaned from Phase 3 code removal are cleaned here.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Brief #6.0 Phase 4: starting DB cleanup")

    # ── 1. Drop orphaned columns ──
    columns_to_drop = {
        'casafolino_mail_message': ['policy_applied_id'],
        'casafolino_mail_sender_decision': ['sender_policy_id'],
        'casafolino_mail_account': ['use_allowlist'],
    }

    for table, cols in columns_to_drop.items():
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = %s
            )
        """, (table,))
        if not cr.fetchone()[0]:
            _logger.info("Brief #6.0: table %s not found, skip", table)
            continue

        for col in cols:
            cr.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                )
            """, (table, col))
            if cr.fetchone()[0]:
                cr.execute(
                    'ALTER TABLE "%s" DROP COLUMN IF EXISTS "%s" CASCADE' % (table, col)
                )
                _logger.info("Brief #6.0: dropped %s.%s", table, col)
            else:
                _logger.info("Brief #6.0: %s.%s not found, skip", table, col)

    # ── 2. Drop sender_policy table ──
    cr.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'casafolino_mail_sender_policy'
        )
    """)
    if cr.fetchone()[0]:
        cr.execute('DROP TABLE IF EXISTS casafolino_mail_sender_policy CASCADE')
        _logger.info("Brief #6.0: dropped table casafolino_mail_sender_policy")

    # ── 3. Drop triage_wizard table (transient, should be empty) ──
    cr.execute('DROP TABLE IF EXISTS casafolino_mail_triage_wizard CASCADE')
    _logger.info("Brief #6.0: dropped table casafolino_mail_triage_wizard")

    # ── 4. Cleanup ir_model_data orphans ──
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'casafolino_mail'
          AND (
            name LIKE 'model_casafolino_mail_sender_policy%'
            OR name LIKE 'model_casafolino_mail_triage_wizard%'
            OR name LIKE 'field_casafolino_mail_sender_policy%'
            OR name LIKE 'field_casafolino_mail_triage_wizard%'
            OR name LIKE 'selection__casafolino_mail_sender_policy%'
            OR name = 'casafolino_mail_triage_wizard_form'
            OR name = 'action_start_orphan_triage'
            OR name = 'casafolino_mail_policy_list'
            OR name = 'casafolino_mail_policy_form'
            OR name = 'casafolino_mail_policy_search'
            OR name = 'action_casafolino_mail_policy'
            OR name = 'menu_casafolino_mail_triage_orphan'
            OR name = 'menu_casafolino_mail_policy'
            OR name LIKE 'access_casafolino_mail_sender_policy%'
            OR name LIKE 'access_casafolino_mail_triage_wizard%'
          )
    """)
    _logger.info("Brief #6.0: cleaned ir_model_data orphans")

    # ── 5. Delete crons + server actions FIRST (FK dependencies) ──
    _removed_models = (
        'casafolino.mail.sender_policy',
        'casafolino.mail.triage.wizard',
    )
    cr.execute("""
        DELETE FROM ir_cron
        WHERE ir_act_server_id IN (
            SELECT id FROM ir_act_server
            WHERE model_id IN (
                SELECT id FROM ir_model WHERE model IN %s
            )
        )
    """, (_removed_models,))
    cr.execute("""
        DELETE FROM ir_act_server
        WHERE model_id IN (
            SELECT id FROM ir_model WHERE model IN %s
        )
    """, (_removed_models,))
    _logger.info("Brief #6.0: cleaned ir_cron + ir_act_server orphans")

    # ── 6. Cleanup ir_model_access ──
    cr.execute("""
        DELETE FROM ir_model_access
        WHERE name LIKE '%%sender_policy%%' OR name LIKE '%%triage_wizard%%'
    """)

    # ── 7. Cleanup ir_act_window ──
    cr.execute("""
        DELETE FROM ir_act_window WHERE res_model IN %s
    """, (_removed_models,))

    # ── 8. Cleanup ir_ui_view ──
    cr.execute("""
        DELETE FROM ir_ui_view WHERE model IN %s
    """, (_removed_models,))

    # ── 9. Cleanup ir_model_fields (before ir_model due to FK) ──
    cr.execute("""
        DELETE FROM ir_model_fields WHERE model IN %s
    """, (_removed_models,))

    # ── 10. Cleanup ir_model LAST ──
    cr.execute("""
        DELETE FROM ir_model WHERE model IN %s
    """, (_removed_models,))
    _logger.info("Brief #6.0: cleaned all ORM orphans")

    _logger.info("Brief #6.0 Phase 4: DB cleanup complete")
