{
    'name': 'CasaFolino Operations',
    'version': '18.0.1.1.0',
    'category': 'CasaFolino',
    'summary': 'Produzione e Mock Recall',
    'author': 'CasaFolino Srls',
    'depends': ['base', 'mail', 'mrp', 'stock', 'purchase', 'sale_management', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'data/cf_creme_workcenter_data.xml',
        'views/cf_production_views.xml',
        'views/cf_recall_views.xml',
        'views/cf_recall_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
