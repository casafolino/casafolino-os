{
    'name': 'CasaFolino Mail',
    'version': '5.0',
    'summary': 'Client email Gmail-style per CasaFolino',
    'category': 'CasaFolino',
    'author': 'CasaFolino',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/cf_mail_views.xml',
        'views/cf_mail_partner_views.xml',
        'views/cf_mail_sender_rule_views.xml',
        'views/menus.xml',
        'data/cf_mail_cron.xml',
        'data/cf_mail_config.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_mail/static/src/css/cf_mail_client.css',
            'casafolino_mail/static/src/xml/cf_mail_client.xml',
            'casafolino_mail/static/src/js/cf_mail_client.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
