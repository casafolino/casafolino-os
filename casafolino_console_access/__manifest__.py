{
    "name": "CasaFolino Console — Access (scoped service user)",
    "version": "18.0.7.1.0",
    "summary": "Service-user Console scoped: console_api (portal, no seat) read+write via ACL + gateway triage sudo + audit. console_prod_rw (S0) dormiente.",
    "description": """
Foundation ACL per l'app Console (Next /console) che autentica via JSON-RPC.
Crea:
  - gruppo group_console_rw
  - utente console_prod_rw (password NON inclusa: la imposta l'admin via UI)
  - ir.model.access: WRITE/CREATE su crm.lead e res.partner (unlink=0)
  - ir.rule group-based: READ tutte le mail (supera 'caselle proprie') + READ/WRITE triage,
    READ/WRITE/CREATE tutti i lead. Nessun perm_unlink → unlink bloccato dalle record-rule.
NEGATO per design: unlink (nessun perm_unlink), account.move/contabilità (nessun ACL),
config res.users/res.company/ir.* (nessun ACL, group_user non scrive).
NB: la write su mail.message è a livello modello (include body): il blocco scrittura-body
è applicato a livello APP (la console scrive solo i campi di triage).
""",
    "category": "Technical",
    "author": "CasaFolino",
    "license": "LGPL-3",
    "depends": ["base", "hr", "crm", "sale", "sales_team", "casafolino_mail", "casafolino_campionatura"],
    "data": [
        "security/console_access_groups.xml",
        "security/console_api_groups.xml",
        "security/console_operator_groups.xml",
        "security/console_manager_groups.xml",
        "security/ir.model.access.csv",
        "security/console_access_rules.xml",
        "security/console_api_rules.xml",
        "data/console_access_user.xml",
        "data/console_api_user.xml",
        "data/console_send_param.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}
