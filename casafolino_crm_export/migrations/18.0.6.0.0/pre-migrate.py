"""
Pre-migration: add stored columns for kanban enrichment.
Backfill casafolino_days_since_last_activity.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('casafolino_crm_export 18.0.6.0.0: pre-migrate kanban enrichment fields')

    # Add cf_category to crm_tag if not exists
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'crm_tag' AND column_name = 'cf_category'
    """)
    if not cr.fetchone():
        cr.execute("ALTER TABLE crm_tag ADD COLUMN cf_category VARCHAR")
        _logger.info('Added cf_category column to crm_tag')

    # Add casafolino_days_since_last_activity to crm_lead if not exists
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'crm_lead' AND column_name = 'casafolino_days_since_last_activity'
    """)
    if not cr.fetchone():
        cr.execute("ALTER TABLE crm_lead ADD COLUMN casafolino_days_since_last_activity INTEGER DEFAULT 0")
        _logger.info('Added casafolino_days_since_last_activity column')

    # Backfill casafolino_days_since_last_activity from write_date
    cr.execute("""
        UPDATE crm_lead
        SET casafolino_days_since_last_activity = GREATEST(0,
            CURRENT_DATE - GREATEST(
                COALESCE(write_date::date, create_date::date),
                COALESCE(date_last_stage_update::date, create_date::date)
            )
        )
        WHERE casafolino_days_since_last_activity = 0 OR casafolino_days_since_last_activity IS NULL
    """)
    _logger.info('Backfilled casafolino_days_since_last_activity for existing leads')
