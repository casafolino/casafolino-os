{
    'name': 'CasaFolino Task Engine',
    'version': '18.0.1.0.0',
    'summary': 'Motore task multi-ruolo: handoff, check-in/out, timer su ore lavorative, semaforo, escalation',
    'category': 'CasaFolino',
    'author': 'CasaFolino',
    'depends': [
        'base',
        'mail',
        'resource',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/work_calendar_data.xml',
        'data/ir_config_parameter_data.xml',
        'views/cf_task_views.xml',
        'views/cf_task_menus.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
