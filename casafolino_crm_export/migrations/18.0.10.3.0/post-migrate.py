import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("[crm_export 10.3.0] Post-migrate: populate primary contacts")

    # For every dossier with partner_id but no contacts yet,
    # create a primary contact derived from the partner
    cr.execute("""
        INSERT INTO cf_project_contact
            (project_id, partner_id, name, email, phone, role,
             is_primary, is_external, sequence,
             create_date, write_date, create_uid, write_uid)
        SELECT
            p.id,
            p.partner_id,
            COALESCE(rp.name, 'Contatto'),
            COALESCE(rp.email, ''),
            COALESCE(rp.phone, rp.mobile, ''),
            'commercial',
            true,
            false,
            10,
            NOW(), NOW(), 1, 1
        FROM project_project p
        JOIN res_partner rp ON rp.id = p.partner_id
        WHERE p.cf_status_dossier IS NOT NULL
          AND p.partner_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM cf_project_contact c
              WHERE c.project_id = p.id
          )
    """)
    count = cr.rowcount
    _logger.info("[crm_export 10.3.0] Created %d primary contacts", count)
