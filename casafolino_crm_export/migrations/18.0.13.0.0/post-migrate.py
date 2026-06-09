import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    C9 fix: backfill cf_date_last_contact da ultimo messaggio email nel chatter.

    I lead importati storicamente hanno cf_date_last_contact = NULL perché il
    campo viene popolato solo da action_mark_contacted() o message_post().
    Questo causa score sempre basso e rotting basato su create_date invece che
    sull'ultimo contatto reale.

    Logica:
    1. Se esiste una email in mail_message per quel lead → prendi la più recente
    2. Altrimenti lascia NULL (il rotting userà create_date come fallback)
    """
    _logger.info('CasaFolino CRM: backfill cf_date_last_contact da chatter email...')

    cr.execute("""
        UPDATE crm_lead l
        SET cf_date_last_contact = sub.last_email_date
        FROM (
            SELECT
                res_id,
                MAX(date)::date AS last_email_date
            FROM mail_message
            WHERE model = 'crm.lead'
              AND message_type IN ('email', 'email_outgoing')
              AND res_id IN (
                  SELECT id FROM crm_lead
                  WHERE type = 'opportunity'
                    AND cf_date_last_contact IS NULL
              )
            GROUP BY res_id
        ) sub
        WHERE l.id = sub.res_id
          AND l.cf_date_last_contact IS NULL
    """)

    updated = cr.rowcount
    _logger.info('CasaFolino CRM: backfill completato — %d lead aggiornati.', updated)

    # Report quanti restano NULL (nessuna email nel chatter)
    cr.execute("""
        SELECT COUNT(*) FROM crm_lead
        WHERE type = 'opportunity'
          AND cf_date_last_contact IS NULL
    """)
    still_null = cr.fetchone()[0]
    if still_null:
        _logger.info(
            'CasaFolino CRM: %d lead ancora con cf_date_last_contact NULL '
            '(nessuna email nel chatter — rotting userà create_date).',
            still_null,
        )
