def migrate(cr, version):
    # Cleanup asset cache for new smart buttons + tab
    cr.execute("""
        DELETE FROM ir_attachment
        WHERE name LIKE '%%web.assets%%' OR url LIKE '/web/assets/%%';
    """)
