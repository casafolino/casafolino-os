# -*- coding: utf-8 -*-
"""Fix seed projects: mark done tasks + post feed messages."""
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

# Tasks to mark as done (by name substring match within project)
_DONE_TASKS = {
    "D'Addezio": ["Loi draft v3"],
    "Stabilimento": ["Progetto layout linee", "Preventivo impiantistica"],
    "Crowdfunding": ["Business plan v4"],
    "Anuga": ["Prenotazione stand"],
    "Linea Fluid": ["Formulazione base 3 linee"],
    "Halal": ["Raccolta documentazione"],
    "Onboarding Whole": ["Listino 2027 USD"],
}

# Messages to post per project
_MESSAGES = {
    "D'Addezio": [
        ("Spalvieri ha inviato draft 3 della LOI. Review notaio in corso.", -2),
        ("Call con D'Addezio: confermata struttura affitto ramo d'azienda.", -5),
    ],
    "Stabilimento": [
        ("Verbale sopralluogo ASL ricevuto, nessuna integrazione richiesta.", -3),
        ("Layout linee approvato. Preventivo impiantistica in negoziazione.", -7),
    ],
    "Crowdfunding": [
        ("Business plan v4 completato. Valutazione pre-money in corso con advisor.", -1),
    ],
    "Anuga": [
        ("Lista buyer aggiornata: 80 contatti confermati, 12 meeting pre-schedulati.", -2),
        ("Stand confermato Hall 7.1, 24mq. Design allestimento in brief.", -6),
    ],
    "Linea Fluid": [
        ("Formulazione base 3 linee completata. Test shelf life avviato.", -4),
    ],
    "IFS": [
        ("Gap analysis pianificata per Q4. Manuale HACCP v3 in aggiornamento.", -3),
    ],
    "Halal": [
        ("Documentazione raccolta completa. Invio domanda rinnovo entro venerdì.", -1),
    ],
    "Onboarding Whole": [
        ("Listino 2027 USD finalizzato. Schede tecniche EN in preparazione.", -2),
        ("Call buyer Whole Foods: richiesta gluten-free statement prioritaria.", -4),
    ],
}


def fix_seed_projects(env):
    """Fix existing seed projects: mark tasks done + post messages."""
    Project = env["project.project"]
    Task = env["project.task"]

    # Mark tasks as done
    for proj_key, task_names in _DONE_TASKS.items():
        projects = Project.search([("name", "ilike", proj_key)], limit=1)
        if not projects:
            continue
        for tname in task_names:
            tasks = Task.search([
                ("project_id", "=", projects.id),
                ("name", "ilike", tname),
            ], limit=1)
            if tasks and tasks.state != "1_done":
                tasks.write({"state": "1_done"})
                _logger.info("Marked task '%s' as done in project '%s'",
                             tname, projects.name)

    # Post messages
    now = datetime.now()
    for proj_key, messages in _MESSAGES.items():
        projects = Project.search([("name", "ilike", proj_key)], limit=1)
        if not projects:
            continue
        for body, days_ago in messages:
            # Check if message already posted (idempotent)
            existing = env["mail.message"].search([
                ("model", "=", "project.project"),
                ("res_id", "=", projects.id),
                ("body", "ilike", body[:40]),
            ], limit=1)
            if existing:
                continue
            projects.message_post(
                body=body,
                subtype_xmlid="mail.mt_comment",
                date=now + timedelta(days=days_ago),
            )
            _logger.info("Posted message on '%s': %s", projects.name, body[:50])

    env.cr.commit()
    _logger.info("Fix seed complete")
