import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("[crm_export 10.4.0] Post-migrate: deactivate obsolete inherits + Vista 360")

    # 1. Deactivate casafolino_project and casafolino_initiative form inherits
    cr.execute("""
        UPDATE ir_ui_view
        SET active = false
        WHERE model = 'project.project'
          AND type = 'form'
          AND priority = 99
          AND active = true
          AND name IN (
              'project.project.form.cf',
              'project.project.form.initiative'
          )
    """)
    _logger.info("[crm_export 10.4.0] Deactivated %d obsolete form inherits", cr.rowcount)

    # 2. Deactivate Vista 360 client action (riattivabile via SQL)
    cr.execute("""
        UPDATE ir_act_client
        SET active = false
        WHERE tag = 'casafolino_crm_export.project_dashboard'
    """)
    _logger.info("[crm_export 10.4.0] Deactivated Vista 360 action: %d rows", cr.rowcount)

    # 3. Clear asset cache
    cr.execute("""
        DELETE FROM ir_attachment
        WHERE name LIKE '%%web.assets%%'
           OR url LIKE '/web/assets/%%'
    """)
    _logger.info("[crm_export 10.4.0] Cleared %d asset cache entries", cr.rowcount)
