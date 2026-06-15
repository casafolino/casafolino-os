{
    'name': 'CasaFolino Console CRM',
    'version': '18.0.1.27.10',
    'category': 'CasaFolino',
    'summary': 'Console CRM export: follow-up, inbox commerciale, pipeline e dossier',
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
        'security/ir.model.access.csv',
        'views/pipeline_control_views.xml',
        'data/legacy_cleanup.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_pipeline_control/static/src/pipeline_control/pipeline_control.js',
            'casafolino_pipeline_control/static/src/pipeline_control/pipeline_control.xml',
            'casafolino_pipeline_control/static/src/pipeline_control/pipeline_control.scss',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
