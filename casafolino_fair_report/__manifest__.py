{
    'name': 'CasaFolino Fair Report',
    'version': '18.0.0.1.0',
    'category': 'CasaFolino',
    'summary': 'Report HTML fine fiera con dashboard metriche, engagement e action items',
    'author': 'CasaFolino Srls',
    'depends': [
        'mail',
        'mass_mailing',
        'crm',
        'casafolino_commercial',
        'casafolino_mail_stats',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/casafolino_fiera_views.xml',
        'views/fair_report_wizard_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
