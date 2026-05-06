"""
Post-migration: backfill cf_partner_role on existing partners.
Order: internal → supplier → customer → prospect (most specific first).
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('casafolino_crm_export 18.0.8.0.0: backfill cf_partner_role')

    # 1. Internal CasaFolino: users with @casafolino.com login
    cr.execute("""
        UPDATE res_partner
        SET cf_partner_role = 'internal'
        WHERE id IN (
            SELECT partner_id FROM res_users
            WHERE login LIKE '%%@casafolino.com'
        )
        AND (cf_partner_role IS NULL OR cf_partner_role = 'other')
    """)
    _logger.info('  internal: %d', cr.rowcount)

    # 2. Suppliers: partner with supplier_rank > 0
    cr.execute("""
        UPDATE res_partner
        SET cf_partner_role = 'supplier'
        WHERE supplier_rank > 0
          AND (cf_partner_role IS NULL OR cf_partner_role = 'other')
    """)
    _logger.info('  supplier: %d', cr.rowcount)

    # 3. Customers: company partners with confirmed sale orders
    cr.execute("""
        UPDATE res_partner p
        SET cf_partner_role = 'customer'
        WHERE EXISTS (
            SELECT 1 FROM sale_order so
            WHERE so.partner_id = p.id
              AND so.state IN ('sale', 'done')
        )
        AND (p.cf_partner_role IS NULL OR p.cf_partner_role = 'other')
        AND p.is_company = true
    """)
    _logger.info('  customer: %d', cr.rowcount)

    # 4. Prospects: company partners with active CRM leads
    cr.execute("""
        UPDATE res_partner p
        SET cf_partner_role = 'prospect'
        WHERE EXISTS (
            SELECT 1 FROM crm_lead l
            WHERE l.partner_id = p.id
              AND l.active = true
        )
        AND (p.cf_partner_role IS NULL OR p.cf_partner_role = 'other')
        AND p.is_company = true
    """)
    _logger.info('  prospect: %d', cr.rowcount)

    # Final stats
    cr.execute("""
        SELECT cf_partner_role, COUNT(*)
        FROM res_partner
        WHERE active = true
        GROUP BY cf_partner_role
        ORDER BY count DESC
    """)
    rows = cr.fetchall()
    _logger.info('  Final distribution:')
    for role, count in rows:
        _logger.info('    %s: %d', role or 'NULL', count)
