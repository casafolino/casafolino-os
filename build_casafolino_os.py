#!/usr/bin/env python3
"""
CasaFolino OS — Build Script
Crea tutti i moduli in /docker/enterprise18/addons/custom/
Esegui con: sudo python3 build_casafolino_os.py
"""
import os

BASE = '/docker/enterprise18/addons/custom'

MODULES = {

# =============================================================================
# 1. CASAFOLINO ALLERGEN
# =============================================================================
'casafolino_allergen/__init__.py': 'from . import models\n',
'casafolino_allergen/__manifest__.py': '''\
# -*- coding: utf-8 -*-
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
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_allergen/models/__init__.py': '# models\n',
'casafolino_allergen/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_allergen_root" name="Allergeni" sequence="27"/>
</odoo>
''',
'casafolino_allergen/data/cf_allergen_14eu.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
</odoo>
''',
'casafolino_allergen/data/cf_allergen_keywords.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
</odoo>
''',
'casafolino_allergen/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 2. CASAFOLINO HACCP
# =============================================================================
'casafolino_haccp/__init__.py': 'from . import models\n',
'casafolino_haccp/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino HACCP",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "HACCP Manager nativo Odoo 18",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_haccp/models/__init__.py': '# models\n',
'casafolino_haccp/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_haccp_root" name="HACCP" sequence="25"/>
</odoo>
''',
'casafolino_haccp/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 3. CASAFOLINO CRM EXPORT
# =============================================================================
'casafolino_crm_export/__init__.py': 'from . import models\n',
'casafolino_crm_export/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino CRM Export",
    "version": "18.0.2.0.0",
    "category": "Sales/CRM",
    "summary": "CRM Export B2B — Pipeline, Scoring, Sequenze, Fiere",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_crm_export/models/__init__.py': '# models\n',
'casafolino_crm_export/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_export_root" name="Export CRM" sequence="20"/>
</odoo>
''',
'casafolino_crm_export/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 4. CASAFOLINO TREASURY
# =============================================================================
'casafolino_treasury/__init__.py': 'from . import models\n',
'casafolino_treasury/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Treasury",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Tesoreria e Cash Flow",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "account", "sale_management", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_treasury/models/__init__.py': '# models\n',
'casafolino_treasury/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_treasury_root" name="Tesoreria" sequence="30"/>
</odoo>
''',
'casafolino_treasury/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 5. CASAFOLINO KPI
# =============================================================================
'casafolino_kpi/__init__.py': 'from . import models\n',
'casafolino_kpi/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino KPI Dashboard",
    "version": "18.0.1.0.0",
    "category": "Reporting",
    "summary": "Dashboard KPI unificata per Antonio",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "purchase", "account", "mrp", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_kpi/models/__init__.py': '# models\n',
'casafolino_kpi/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_kpi_root" name="KPI" sequence="10"/>
</odoo>
''',
'casafolino_kpi/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 6. CASAFOLINO GDO
# =============================================================================
'casafolino_gdo/__init__.py': 'from . import models\n',
'casafolino_gdo/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino GDO",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Pipeline GDO — Listing, Contratti, Forecast",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_gdo/models/__init__.py': '# models\n',
'casafolino_gdo/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_gdo_root" name="GDO" sequence="35"/>
</odoo>
''',
'casafolino_gdo/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 7. CASAFOLINO PRIVATE LABEL
# =============================================================================
'casafolino_private_label/__init__.py': 'from . import models\n',
'casafolino_private_label/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Private Label",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Gestione clienti Private Label",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "sale_management", "product", "account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_private_label/models/__init__.py': '# models\n',
'casafolino_private_label/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_pl_root" name="Private Label" sequence="40"/>
</odoo>
''',
'casafolino_private_label/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 8. CASAFOLINO PRODUCTION
# =============================================================================
'casafolino_production/__init__.py': 'from . import models\n',
'casafolino_production/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Production Calendar",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Commesse produzione con calendario Gantt",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "project", "mrp", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_production/models/__init__.py': '# models\n',
'casafolino_production/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_prod_root" name="Produzione" sequence="22"/>
</odoo>
''',
'casafolino_production/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 9. CASAFOLINO NUTRITION
# =============================================================================
'casafolino_nutrition/__init__.py': 'from . import models\n',
'casafolino_nutrition/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Nutrition",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Valori nutrizionali da BoM + etichette PDF",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_nutrition/models/__init__.py': '# models\n',
'casafolino_nutrition/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_nutrition_root" name="Nutrizione" sequence="28"/>
</odoo>
''',
'casafolino_nutrition/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 10. CASAFOLINO RECALL
# =============================================================================
'casafolino_recall/__init__.py': 'from . import models\n',
'casafolino_recall/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Mock Recall",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Mock Recall BRC/IFS — Tracciabilita lotti",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "mrp", "stock", "purchase", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_recall/models/__init__.py': '# models\n',
'casafolino_recall/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_recall_root" name="Mock Recall" sequence="29"/>
</odoo>
''',
'casafolino_recall/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

# =============================================================================
# 11. CASAFOLINO SUPPLIER QUAL
# =============================================================================
'casafolino_supplier_qual/__init__.py': 'from . import models\n',
'casafolino_supplier_qual/__manifest__.py': '''\
# -*- coding: utf-8 -*-
{
    "name": "CasaFolino Supplier Qualification",
    "version": "18.0.1.0.0",
    "category": "Purchase",
    "summary": "Qualifica fornitori BRC/IFS",
    "author": "CasaFolino Srls",
    "depends": ["base", "mail", "purchase", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
''',
'casafolino_supplier_qual/models/__init__.py': '# models\n',
'casafolino_supplier_qual/views/menus.xml': '''\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_cf_supplier_qual_root" name="Fornitori Qualificati" sequence="32"/>
</odoo>
''',
'casafolino_supplier_qual/security/ir.model.access.csv': 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n',

}

# =============================================================================
# BUILD
# =============================================================================
created_dirs  = 0
created_files = 0

for rel_path, content in MODULES.items():
    full_path = os.path.join(BASE, rel_path)
    dir_path  = os.path.dirname(full_path)

    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        created_dirs += 1

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    created_files += 1
    print(f'  ✅ {rel_path}')

print(f'\n🎉 Build completato!')
print(f'   Cartelle create: {created_dirs}')
print(f'   File creati:     {created_files}')
print(f'\nProssimo passo:')
print(f'  sudo docker exec odoo-app odoo -d folinofood-stage --update=all --stop-after-init')
