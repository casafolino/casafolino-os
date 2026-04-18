import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """v7.10.2 — triage form via transient wizard (not SQL view).

    Cleanup obsolete compute fields from orphan_partner model registry
    and old ir.ui.view / ir.actions.server that pointed to orphan model.
    """
    # Pulizia campi compute obsoleti dalla view orphan_partner
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model = 'casafolino.mail.orphan.partner'
          AND name IN ('decision_id', 'is_triaged', 'triage_decision',
                       'last_email_subject', 'last_email_body_preview')
    """)
    removed = cr.rowcount
    _logger.info(
        "casafolino_mail 7.10.2: removed %d obsolete compute fields "
        "from orphan_partner model registry", removed
    )

    # Pulizia vecchia view triage form che puntava a orphan_partner
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'casafolino_mail'
          AND name = 'casafolino_mail_orphan_triage_form'
    """)
    if cr.rowcount:
        _logger.info("casafolino_mail 7.10.2: removed old triage form ir_model_data ref")

    # Pulizia vecchio server action che puntava a orphan_partner
    cr.execute("""
        UPDATE ir_model_data
        SET module = 'casafolino_mail'
        WHERE module = 'casafolino_mail'
          AND name = 'action_start_orphan_triage'
    """)
    _logger.info("casafolino_mail 7.10.2: migration complete — triage now uses transient wizard")
