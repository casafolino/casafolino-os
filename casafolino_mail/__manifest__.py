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
        'data/cf_mail_cron.xml',
    ],
    'assets': {
        'web.assets_web': [
            'casafolino_mail/static/src/css/cf_mail_client.css',
            'casafolino_mail/static/src/xml/cf_mail_client.xml',
            'casafolino_mail/static/src/js/cf_mail_client.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
