import os

BASE = '/docker/enterprise18/addons/custom/casafolino_allergen'

files = {
'__init__.py': 'from . import models\n',

'__manifest__.py': '''# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Allergeni",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Gestione 14 allergeni UE per ricette — Reg. 1169/2011",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/cf_allergen_14eu.xml",
        "data/cf_allergen_keywords.xml",
        "views/cf_allergen_views.xml",
        "views/cf_recipe_allergen_views.xml",
        "views/cf_bom_allergen_views.xml",
        "views/menus.xml",
        "report/cf_allergen_declaration_report.xml",
        "report/cf_allergen_declaration_template.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',

'models/__init__.py': '''from . import cf_allergen
from . import cf_allergen_keyword
from . import cf_recipe_allergen
''',
}

dirs = [
    BASE,
    f'{BASE}/models',
    f'{BASE}/views',
    f'{BASE}/data',
    f'{BASE}/security',
    f'{BASE}/report',
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f'✅ Cartella: {d}')

for path, content in files.items():
    full = f'{BASE}/{path}'
    with open(full, 'w') as f:
        f.write(content)
    print(f'✅ File: {full}')

print('\n🎉 Struttura casafolino_allergen creata.')
