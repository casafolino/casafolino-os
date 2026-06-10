{
    'name': 'CasaFolino Cockpit',
    'version': '18.0.1.0.0',
    'category': 'CasaFolino',
    'summary': 'Cockpit parallelo beta — staffetta + dossier clienti',
    'depends': ['casafolino_initiative', 'casafolino_initiative_dashboard', 'casafolino_mail', 'base'],
    'data': [
        'security/cf_cockpit_security.xml',
        'security/ir.model.access.csv',
        'views/cf_cockpit_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_cockpit/static/src/scss/cockpit.scss',
            'casafolino_cockpit/static/src/js/cockpit_main.js',
            'casafolino_cockpit/static/src/js/cockpit_regia.js',
            'casafolino_cockpit/static/src/js/cockpit_dossier.js',
            'casafolino_cockpit/static/src/xml/cockpit_main.xml',
            'casafolino_cockpit/static/src/xml/cockpit_regia.xml',
            'casafolino_cockpit/static/src/xml/cockpit_dossier.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'OPL-1',
}
