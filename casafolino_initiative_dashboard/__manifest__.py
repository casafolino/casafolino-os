{
    'name': 'CasaFolino Initiative Dashboard',
    'version': '18.0.1.0.0',
    'summary': 'Lavagna cockpit + wizard setup per iniziative CasaFolino',
    'category': 'CasaFolino',
    'author': 'CasaFolino',
    'depends': [
        'casafolino_initiative',
        'project',
        'mail',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cf_initiative_tag_source_data.xml',
        'data/dashboard_kpi_data.xml',
        'data/lavagna_template_data.xml',
        'views/cf_initiative_views.xml',
        'views/dashboard_kpi_views.xml',
        'views/lavagna_template_views.xml',
        'wizard/cf_initiative_wizard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_initiative_dashboard/static/src/js/dashboard_placeholder.js',
            'casafolino_initiative_dashboard/static/src/xml/dashboard_placeholder.xml',
            'casafolino_initiative_dashboard/static/src/css/wizard.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
