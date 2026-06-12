import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        SELECT res_id
          FROM ir_model_data
         WHERE module = 'casafolino_mail'
           AND name = 'menu_casafolino_mail_root'
           AND model = 'ir.ui.menu'
         LIMIT 1
    """)
    row = cr.fetchone()
    if not row:
        _logger.warning("[V19.4] Mail Inbox V2 root menu not found")
        return

    root_id = row[0]
    cr.execute("""
        UPDATE ir_ui_menu
           SET active = false
         WHERE parent_id = %s
           AND id NOT IN (
               SELECT res_id
                 FROM ir_model_data
                WHERE module = 'casafolino_mail'
                  AND name = 'menu_casafolino_mail_my_mailbox'
                  AND model = 'ir.ui.menu'
           )
           AND active = true
    """, (root_id,))
    _logger.info("[V19.4] Disabled %s legacy Mail Inbox V2 child menus", cr.rowcount)
