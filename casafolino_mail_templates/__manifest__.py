{
    'name': 'CasaFolino Mail Templates',
    'version': '18.0.0.1.0',
    'summary': 'Gestione template email centralizzata in Mail Hub con tag, snippet e wizard fiera',
    'category': 'CasaFolino',
    'author': 'CasaFolino',
    'depends': [
        'mail',
        'mass_mailing',
        'crm',
        'casafolino_mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_tag_data.xml',
        'data/mail_snippet_data.xml',
        'wizard/mail_template_fair_wizard_views.xml',
        'views/mail_template_views.xml',
        'views/mail_template_tag_views.xml',
        'views/mail_snippet_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'casafolino_mail_templates/static/src/components/snippet_picker/snippet_picker.js',
            'casafolino_mail_templates/static/src/components/snippet_picker/snippet_picker.xml',
            'casafolino_mail_templates/static/src/components/snippet_picker/snippet_picker.scss',
        ],
    },
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
