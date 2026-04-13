{
    'name': 'CasaFolino Labels',
    'version': '18.0.1.0.0',
    'category': 'CasaFolino',
    'summary': 'Pipeline gestione etichette prodotti',
    'depends': ['base', 'mail', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/cf_label_views.xml',
        'views/cf_label_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
