{
    'name': 'CasaFolino BackOperation',
    'version': '18.0.1.0.0',
    'summary': 'Lente PWA task operativi reparto: pool, claim, check-in/out, firma su cf.task',
    'description': """
BackOperation (Livello A)
=========================
Estende cf.task per la PWA esterna usata dalle operative di produzione.
Tracciabilità operatore (hr.employee reale) su ogni esecuzione/firma per audit IFS/BRC.
NON consuma componenti né chiude l'MO in Odoo (round 2).
""",
    'category': 'CasaFolino',
    'author': 'CasaFolino',
    'depends': [
        'casafolino_task',
        'mrp',
        'hr',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/cf_backoperation_views.xml',
        'views/cf_backoperation_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
