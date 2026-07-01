# casafolino_console_access — ACL scoped per gli utenti di servizio della Console.
# S0: console_prod_rw (internal, dormiente). console_api (portal, no seat) con gateway
# triage/send/reply sudo + audit + sponde S4 (cap/dedup/burst/digest).
# S5: group_console_operator (allowlist umani) + attribution operatore nel gateway.
from . import models

# Login degli operatori umani abilitati alla Console (allowlist unica S5).
CONSOLE_OPERATOR_LOGINS = (
    'antonio@casafolino.com',
    'martina.sinopoli@casafolino.com',
    'josefina.lazzaro@casafolino.com',
)


def _ensure_console_operators(env):
    """Aggiunge gli operatori umani (per login) al group_console_operator. Idempotente.
    Chiamato sia da post_init_hook (install) sia dalla migration (update). Non rimuove
    membri esistenti aggiunti a mano via UI."""
    import logging
    _logger = logging.getLogger(__name__)
    group = env.ref('casafolino_console_access.group_console_operator', raise_if_not_found=False)
    if not group:
        _logger.warning("[console S5] group_console_operator assente: skip membri.")
        return
    for login in CONSOLE_OPERATOR_LOGINS:
        user = env['res.users'].sudo().search([('login', '=', login)], limit=1)
        if not user:
            user = env['res.users'].sudo().search([('email', '=ilike', login)], limit=1)
        if user:
            user.sudo().write({'groups_id': [(4, group.id)]})
            _logger.info("[console S5] %s aggiunto a group_console_operator.", login)
        else:
            _logger.warning("[console S5] utente %s non trovato: assegnare a mano.", login)


# Brief 5 — manager Console (accesso pieno CRM). Sottoinsieme degli operatori.
CONSOLE_MANAGER_LOGINS = (
    'antonio@casafolino.com',
    'martina.sinopoli@casafolino.com',
    'josefina.lazzaro@casafolino.com',
)


def _ensure_console_managers(env):
    """Aggiunge i manager al group_console_manager. Idempotente. Non rimuove membri."""
    import logging
    _logger = logging.getLogger(__name__)
    group = env.ref('casafolino_console_access.group_console_manager', raise_if_not_found=False)
    if not group:
        _logger.warning("[console B5] group_console_manager assente: skip membri.")
        return
    for login in CONSOLE_MANAGER_LOGINS:
        user = env['res.users'].sudo().search([('login', '=', login)], limit=1)
        if not user:
            user = env['res.users'].sudo().search([('email', '=ilike', login)], limit=1)
        if user:
            user.sudo().write({'groups_id': [(4, group.id)]})
            _logger.info("[console B5] %s aggiunto a group_console_manager.", login)
        else:
            _logger.warning("[console B5] manager %s non trovato: assegnare a mano.", login)


# Brief Regia+Dossier — dismissione soft: root menu dei sistemi legacy da occultare.
# Riassegnati al gruppo vuoto cf_legacy_access → spariscono per tutti, moduli intatti.
LEGACY_MENU_XMLIDS = (
    'casafolino_initiative.menu_initiative_root',            # Lavagna (root "Iniziative")
    'casafolino_pipeline_control.menu_cf_pipeline_control',       # Cockpit "Console CRM"
    'casafolino_pipeline_control.menu_cf_pipeline_control_root',  # Cockpit "Console CRM" (root)
)


def _hide_legacy_menus(env):
    """Occulta i menu Lavagna/Cockpit riassegnandoli a cf_legacy_access (gruppo vuoto).
    Idempotente, non distruttivo (moduli restano installati). Reversibile."""
    import logging
    _logger = logging.getLogger(__name__)
    group = env.ref('casafolino_console_access.group_cf_legacy_access', raise_if_not_found=False)
    if not group:
        _logger.warning("[legacy] group_cf_legacy_access assente: skip occultamento menu.")
        return
    for xid in LEGACY_MENU_XMLIDS:
        menu = env.ref(xid, raise_if_not_found=False)
        if menu:
            menu.sudo().write({'groups_id': [(6, 0, [group.id])]})
            _logger.info("[legacy] menu %s (id=%s) occultato → cf_legacy_access.", xid, menu.id)
        else:
            _logger.info("[legacy] menu %s non presente: nulla da occultare.", xid)


def post_init_hook(env):
    """Install: assegna gli operatori e crea il cron digest invii (idempotente).
    Evita model_id ref in XML (ParseError Odoo 18)."""
    from odoo import fields
    _ensure_console_operators(env)
    _ensure_console_managers(env)
    _hide_legacy_menus(env)
    Cron = env['ir.cron'].sudo()
    if Cron.search([('cron_name', '=', 'CasaFolino Console: digest invii')], limit=1):
        return
    model = env['ir.model'].sudo().search([('model', '=', 'casafolino.mail.message')], limit=1)
    if not model:
        return
    Cron.create({
        'name': 'CasaFolino Console: digest invii',
        'model_id': model.id,
        'state': 'code',
        'code': 'model._cron_console_send_digest()',
        'interval_number': 1,
        'interval_type': 'days',
        'active': True,
        'nextcall': fields.Datetime.now(),
    })
