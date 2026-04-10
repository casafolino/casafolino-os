{
    'name': 'CasaFolino Export CRM',
    'version': '18.0.2.0.0',
    'category': 'Sales/CRM',
    'summary': 'CRM Export B2B con scoring, rotting, campionature e fiere',
    'author': 'CasaFolino S.R.L.',
    'depends': ['crm', 'sale', 'mail', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/cf_sample_stages.xml',
        'data/cf_sequence_data.xml',
        'data/cf_export_cron.xml',
        'views/crm_lead_views.xml',
        'views/cf_sample_views.xml',
        'views/cf_fair_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_crm_export/static/src/css/cf_crm.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
