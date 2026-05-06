"""
Post-migration: set cf_category='issue' on existing tags matching complaint keywords.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('casafolino_crm_export 18.0.7.0.0: set issue category on complaint tags')

    cr.execute("""
        UPDATE crm_tag
        SET cf_category = 'issue'
        WHERE cf_category IS NULL
          AND (
              name::text ILIKE '%%reclamo%%' OR
              name::text ILIKE '%%problema%%' OR
              name::text ILIKE '%%non conformit%%' OR
              name::text ILIKE '%%complaint%%' OR
              name::text ILIKE '%%issue%%' OR
              name::text ILIKE '%%difetto%%'
          )
    """)
    updated = cr.rowcount
    _logger.info('Set cf_category=issue on %d tags', updated)
