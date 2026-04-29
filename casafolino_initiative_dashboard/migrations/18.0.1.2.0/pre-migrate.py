"""
F1.2 Migration: Deactivate old 3 templates (1-per-family) and remove their
ir_model_data entries so the new 9 scenario templates can be created cleanly.

Old template XML IDs:
- template_oc_export
- template_ev_fiera
- template_ce_campionatura

Also clean up wizard relation tables that changed names (from dashboard_wizard_*
to wizard_dashboard_*).
"""
import logging

_logger = logging.getLogger(__name__)

OLD_TEMPLATE_XMLIDS = [
    'template_oc_export',
    'template_ev_fiera',
    'template_ce_campionatura',
]

MODULE = 'casafolino_initiative_dashboard'


def migrate(cr, version):
    if not version:
        return

    _logger.info("F1.2 pre-migrate: deactivating old lavagna templates")

    # Deactivate old templates by XML ID
    for xmlid in OLD_TEMPLATE_XMLIDS:
        cr.execute("""
            UPDATE casafolino_lavagna_template
            SET active = false
            WHERE id = (
                SELECT res_id FROM ir_model_data
                WHERE module = %s AND name = %s AND model = 'casafolino.lavagna.template'
            )
        """, (MODULE, xmlid))
        if cr.rowcount:
            _logger.info("  Deactivated template %s", xmlid)
        else:
            _logger.info("  Template %s not found (already removed?)", xmlid)

    # Drop old wizard M2M relation tables if they exist (names changed)
    for old_table in [
        'dashboard_wizard_swimlane_rel',
        'dashboard_wizard_kpi_rel',
        'dashboard_wizard_users_rel',
        'dashboard_wizard_market_tags_rel',
    ]:
        cr.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s
        """, (old_table,))
        if cr.fetchone():
            cr.execute(f"DROP TABLE {old_table}")
            _logger.info("  Dropped old relation table %s", old_table)
