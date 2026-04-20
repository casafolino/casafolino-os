"""F6 migration: lead rules, followup rules, templates, new fields, crons."""
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _ensure_cron(env, name, model, code, interval_number, interval_type):
    """Create cron via ORM if not already present (idempotent)."""
    Cron = env['ir.cron'].sudo()
    existing = Cron.search([('cron_name', 'ilike', name)], limit=1)
    if existing:
        _logger.info("[mail v3 F6] Cron '%s' already exists (id=%s)", name, existing.id)
        return existing

    model_rec = env['ir.model'].search([('model', '=', model)], limit=1)
    if not model_rec:
        _logger.error("[mail v3 F6] Model %s not found, skip cron '%s'", model, name)
        return None

    server_action = env['ir.actions.server'].create({
        'name': name + ' - Action',
        'model_id': model_rec.id,
        'state': 'code',
        'code': code,
    })

    cron = Cron.create({
        'cron_name': name,
        'ir_actions_server_id': server_action.id,
        'interval_number': interval_number,
        'interval_type': interval_type,
        'active': True,
        'user_id': env.ref('base.user_admin').id,
    })
    _logger.info("[mail v3 F6] Created cron '%s' (id=%s)", name, cron.id)
    return cron


def _create_default_lead_rules(env):
    """Create 3 default lead rules."""
    Rule = env['casafolino.mail.lead.rule']
    if Rule.search_count([]) > 0:
        _logger.info("[mail v3 F6] Lead rules already exist, skip defaults")
        return

    # Find stages
    stage_new = env['crm.stage'].search([('name', 'ilike', 'Nuovo')], limit=1)
    stage_qual = env['crm.stage'].search([('name', 'ilike', 'Qualificato')], limit=1)
    if not stage_new:
        stage_new = env['crm.stage'].search([], limit=1)
    if not stage_qual:
        stage_qual = stage_new

    Rule.create({
        'name': 'Hot buyers active >=3 outbound',
        'sequence': 1,
        'min_outbound_messages': 3,
        'max_thread_age_days': 30,
        'min_hotness': 60,
        'exclude_partners_with_open_lead': True,
        'estimated_revenue': 5000.0,
        'stage_id': stage_qual.id if stage_qual else False,
    })
    Rule.create({
        'name': 'Post-fair follow-up active',
        'sequence': 2,
        'min_outbound_messages': 2,
        'max_thread_age_days': 60,
        'min_hotness': 40,
        'require_subject_keywords': 'fiera,fair,anuga,sial,plma,fancy food,ism,biofach,marca',
        'exclude_partners_with_open_lead': True,
        'estimated_revenue': 10000.0,
        'stage_id': stage_new.id if stage_new else False,
    })
    Rule.create({
        'name': 'Sample requests',
        'sequence': 3,
        'min_outbound_messages': 1,
        'max_thread_age_days': 30,
        'min_hotness': 30,
        'require_subject_keywords': 'sample,campione,muestra,sampling',
        'exclude_partners_with_open_lead': True,
        'estimated_revenue': 3000.0,
        'stage_id': stage_new.id if stage_new else False,
    })
    _logger.info("[mail v3 F6] Created 3 default lead rules")


def _create_default_followup_rules(env):
    """Create 2 default follow-up rules."""
    Rule = env['casafolino.mail.followup.rule']
    if Rule.search_count([]) > 0:
        _logger.info("[mail v3 F6] Followup rules already exist, skip defaults")
        return

    todo_type = env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

    Rule.create({
        'name': 'Hot thread no reply 7gg',
        'sequence': 1,
        'min_hotness': 70,
        'no_reply_days': 7,
        'min_outbound_messages': 1,
        'max_thread_age_days': 60,
        'action_type': 'activity',
        'activity_type_id': todo_type.id if todo_type else False,
        'activity_summary': 'Follow-up thread caldo (7gg senza reply)',
        'activity_note': 'Thread con hotness >=70 senza reply da 7 giorni. Valutare follow-up.',
        'activity_user_field': 'thread_user',
        'activity_deadline_days': 2,
        'skip_if_activity_last_days': 3,
    })
    Rule.create({
        'name': 'Super hot no reply 3gg',
        'sequence': 2,
        'min_hotness': 85,
        'no_reply_days': 3,
        'min_outbound_messages': 1,
        'max_thread_age_days': 60,
        'action_type': 'activity',
        'activity_type_id': todo_type.id if todo_type else False,
        'activity_summary': 'URGENTE: Super hot thread senza reply (3gg)',
        'activity_note': 'Thread con hotness >=85 senza reply da 3 giorni. Azione immediata.',
        'activity_user_field': 'partner_user',
        'activity_deadline_days': 1,
        'skip_if_activity_last_days': 2,
    })
    _logger.info("[mail v3 F6] Created 2 default followup rules")


def _create_default_templates(env):
    """Create 6 default email templates."""
    Template = env['casafolino.mail.template']
    if Template.search_count([]) > 0:
        _logger.info("[mail v3 F6] Templates already exist, skip defaults")
        return

    templates = [
        {
            'name': 'Follow-up post incontro',
            'sequence': 1,
            'category': 'follow_up',
            'language': 'it_IT',
            'subject': 'Follow-up: {{thread_subject}}',
            'body_html': '<p>Gentile {{partner_first_name}},</p>'
                         '<p>grazie per il piacevole incontro. Come discusso, le invio un riepilogo '
                         'dei nostri prodotti artigianali calabresi che potrebbero interessare la vostra distribuzione.</p>'
                         '<p>Resto a disposizione per campionature o informazioni aggiuntive.</p>'
                         '<p>Cordiali saluti,<br/>{{sender_name}}</p>',
        },
        {
            'name': 'Follow-up after meeting',
            'sequence': 2,
            'category': 'follow_up',
            'language': 'en_US',
            'subject': 'Follow-up: {{thread_subject}}',
            'body_html': '<p>Dear {{partner_first_name}},</p>'
                         '<p>Thank you for the pleasant meeting. As discussed, I am sending you a summary '
                         'of our artisan Calabrian products that could be of interest for your distribution.</p>'
                         '<p>I remain available for samples or additional information.</p>'
                         '<p>Best regards,<br/>{{sender_name}}</p>',
        },
        {
            'name': 'Nachverfolgung nach Messe',
            'sequence': 3,
            'category': 'post_fair',
            'language': 'de_DE',
            'subject': 'Nachverfolgung: {{thread_subject}}',
            'body_html': '<p>Sehr geehrte/r {{partner_first_name}},</p>'
                         '<p>vielen Dank für Ihren Besuch an unserem Stand. Wie besprochen, sende ich Ihnen '
                         'eine Übersicht unserer handwerklichen kalabrischen Produkte.</p>'
                         '<p>Für Muster oder weitere Informationen stehe ich Ihnen gerne zur Verfügung.</p>'
                         '<p>Mit freundlichen Grüßen,<br/>{{sender_name}}</p>',
        },
        {
            'name': 'Invio campioni CasaFolino',
            'sequence': 4,
            'category': 'sample_offer',
            'language': 'it_IT',
            'subject': 'Campionatura CasaFolino per {{partner_name}}',
            'body_html': '<p>Gentile {{partner_first_name}},</p>'
                         '<p>come da accordi, abbiamo preparato la campionatura dei nostri prodotti '
                         'artigianali per la vostra valutazione.</p>'
                         '<p>Il pacco verrà spedito entro 48h. Vi comunicherò il tracking appena disponibile.</p>'
                         '<p>Ultimo ordine: {{last_order_date}}</p>'
                         '<p>Cordiali saluti,<br/>{{sender_name}}</p>',
        },
        {
            'name': 'Sample shipment from CasaFolino',
            'sequence': 5,
            'category': 'sample_offer',
            'language': 'en_US',
            'subject': 'CasaFolino sample shipment for {{partner_name}}',
            'body_html': '<p>Dear {{partner_first_name}},</p>'
                         '<p>As agreed, we have prepared a sample box of our artisan products '
                         'for your evaluation.</p>'
                         '<p>The parcel will be shipped within 48h. I will share the tracking once available.</p>'
                         '<p>Best regards,<br/>{{sender_name}}</p>',
        },
        {
            'name': 'Offerta commerciale',
            'sequence': 6,
            'category': 'quote',
            'language': 'it_IT',
            'subject': 'Offerta commerciale CasaFolino — {{partner_name}}',
            'body_html': '<p>Gentile {{partner_first_name}},</p>'
                         '<p>in allegato trova la nostra offerta commerciale personalizzata.</p>'
                         '<p>I prezzi indicati sono validi per 30 giorni dalla data odierna ({{today_date}}).</p>'
                         '<p>Resto a disposizione per qualsiasi chiarimento.</p>'
                         '<p>Cordiali saluti,<br/>{{sender_name}}</p>',
        },
    ]

    for vals in templates:
        Template.create(vals)
    _logger.info("[mail v3 F6] Created 6 default email templates")


def migrate(cr, version):
    _logger.info('[mail v3 F6] Starting migration 18.0.8.5.0')
    env = api.Environment(cr, SUPERUSER_ID, {})

    # ── 1. Add fields to crm_lead ──
    cr.execute("""
        ALTER TABLE crm_lead
        ADD COLUMN IF NOT EXISTS cf_mail_thread_id INTEGER;
    """)
    cr.execute("""
        ALTER TABLE crm_lead
        ADD COLUMN IF NOT EXISTS cf_auto_created BOOLEAN DEFAULT false;
    """)
    cr.execute("""
        ALTER TABLE crm_lead
        ADD COLUMN IF NOT EXISTS cf_mail_lead_rule_id INTEGER;
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_crm_lead_cf_mail_thread_id
        ON crm_lead (cf_mail_thread_id) WHERE cf_mail_thread_id IS NOT NULL;
    """)

    # ── 2. Add field to sale_order ──
    cr.execute("""
        ALTER TABLE sale_order
        ADD COLUMN IF NOT EXISTS cf_mail_thread_id INTEGER;
    """)
    cr.execute("""
        CREATE INDEX IF NOT EXISTS idx_sale_order_cf_mail_thread_id
        ON sale_order (cf_mail_thread_id) WHERE cf_mail_thread_id IS NOT NULL;
    """)

    # ── 3. Add undo_send_seconds to res_users ──
    cr.execute("""
        ALTER TABLE res_users
        ADD COLUMN IF NOT EXISTS mv3_undo_send_seconds INTEGER DEFAULT 10;
    """)

    # ── 4. Cron 94: Auto-link Leads (every 4 hours) ──
    _ensure_cron(env,
                 name='Mail V3: Auto-link Leads',
                 model='casafolino.mail.lead.rule',
                 code='model._cron_auto_link_leads()',
                 interval_number=4, interval_type='hours')

    # ── 5. Cron 95: Follow-up Checker (every 2 hours) ──
    _ensure_cron(env,
                 name='Mail V3: Follow-up Checker',
                 model='casafolino.mail.followup.rule',
                 code='model._cron_followup_check()',
                 interval_number=2, interval_type='hours')

    # ── 6. Default lead rules ──
    _create_default_lead_rules(env)

    # ── 7. Default followup rules ──
    _create_default_followup_rules(env)

    # ── 8. Default templates ──
    _create_default_templates(env)

    _logger.info('[mail v3 F6] Migration 18.0.8.5.0 complete')
