{
    'name': 'CasaFolino Pipeline Control',
    'version': '18.0.1.0.7',
    'category': 'CasaFolino',
    'summary': 'Sala controllo export: follow-up, inbox commerciale, pipeline e dossier',
    'author': 'CasaFolino S.R.L.',
    'depends': [
        'crm',
        'mail',
        'sale',
        'project',
        'casafolino_crm_export',
        'casafolino_mail',
        'casafolino_project',
    ],
    'data': [
        'views/pipeline_control_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_pipeline_control/static/src/pipeline_control/pipeline_control.js',
            'casafolino_pipeline_control/static/src/pipeline_control/pipeline_control.xml',
            'casafolino_pipeline_control/static/src/pipeline_control/pipeline_control.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
