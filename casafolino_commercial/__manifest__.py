{
    'name': 'CasaFolino Commercial',
    'version': '18.0.1.0.0',
    'category': 'CasaFolino',
    'summary': 'GDO, Private Label e Tesoreria',
    'author': 'CasaFolino Srls',
    'depends': ['base', 'mail', 'sale_management', 'product', 'account', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/cf_treasury_cron.xml',
        'views/cf_gdo_views.xml',
        'views/cf_pl_views.xml',
        'views/cf_treasury_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            ('prepend', 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'),
            'casafolino_commercial/static/src/xml/cf_treasury_dashboard.xml',
            'casafolino_commercial/static/src/js/cf_treasury_dashboard.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
