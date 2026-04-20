{
    'name': 'CasaFolino Mail CRM',
    'version': '18.0.8.2.0',
    'summary': 'Cockpit commerciale Mail V3 + Intelligence per CasaFolino',
    'category': 'CasaFolino',
    'author': 'CasaFolino',
    'depends': ['base', 'mail', 'web', 'utm', 'crm', 'sale', 'account', 'contacts', 'casafolino_crm_export'],
    'data': [
        # security FIRST
        'security/mail_v3_groups.xml',
        'security/mail_v3_rules.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        # existing views
        'views/casafolino_mail_hub_views.xml',
        'views/intelligence_views.xml',
        'views/casafolino_mail_policy_views.xml',
        'views/casafolino_mail_wizard_views.xml',
        'views/sla_partner_views.xml',
        'views/orphan_partner_views.xml',
        'views/lead_score_views.xml',
        'views/snippet_views.xml',
        'views/snippet_picker_views.xml',
        'views/triage_wizard_views.xml',
        'views/sender_decision_views.xml',
        'views/menus.xml',
        # V3 views + menus
        'views/mail_v3_menus.xml',
        # existing data
        'data/snippet_seed.xml',
        'data/cf_mail_cron.xml',
        'data/cf_mail_config.xml',
        'data/cf_utm_sources.xml',
        'data/casafolino_mail_server_actions.xml',
        'data/casafolino_mail_hub_cron.xml',
        # V3 data
        'data/mail_v3_config.xml',
        'data/mail_v3_signatures_seed.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_mail/static/src/js/snippet_clipboard.js',
            'casafolino_mail/static/src/xml/snippet_clipboard.xml',
            'casafolino_mail/static/src/js/triage_shortcuts.js',
            # V3 assets
            'casafolino_mail/static/src/scss/mail_v3.scss',
            'casafolino_mail/static/src/js/mail_v3/**/*.js',
            'casafolino_mail/static/src/xml/mail_v3/*.xml',
        ],
    },
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
