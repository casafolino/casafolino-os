# -*- coding: utf-8 -*-
"""Post-init hook to seed 8 CasaFolino projects with tasks."""
import logging
from datetime import date, timedelta

_logger = logging.getLogger(__name__)

_PROJECTS = [
    {
        "name": "D'Addezio acquisition",
        "tag": "Acquisizione",
        "date": "2026-12-31",
        "desc": "Acquisizione branch-of-business D'Addezio S.R.L. Loi entro 20 novembre 2026, struttura affitto di ramo d'azienda con opzione acquisto",
        "partner_search": "D'Addezio",
        "owner": "antonio",
        "tasks": [
            {"name": "Loi draft v3", "done": True, "days": -20},
            {"name": "Review notaio", "done": False, "days": 5, "priority": "1"},
            {"name": "Firma Loi", "done": False, "days": 14},
            {"name": "Due diligence finanziaria", "done": False, "days": 30},
            {"name": "Setup affitto ramo", "done": False, "days": 60},
        ],
    },
    {
        "name": "Stabilimento nuovo Lamezia",
        "tag": "Infrastruttura",
        "date": "2027-03-31",
        "desc": "Trasferimento operativo nuovo capannone 65x20m, 6 linee produzione, certificazioni IFS/BRC sul nuovo sito",
        "partner_search": None,
        "owner": "antonio",
        "tasks": [
            {"name": "Progetto layout linee", "done": True, "days": -30},
            {"name": "Preventivo impiantistica", "done": True, "days": -15},
            {"name": "Contratto affitto capannone", "done": False, "days": 10},
            {"name": "Ordine macchinari", "done": False, "days": 45},
            {"name": "Avvio cantiere", "done": False, "days": 90},
        ],
    },
    {
        "name": "Crowdfunding €4M",
        "tag": "Finanza",
        "date": "2026-12-15",
        "desc": "Round equity crowdfunding €4M, pre-money €10-12M, target revenue €15M by 2030. Pipeline GDO Aldi/Rewe/Whole Foods",
        "partner_search": None,
        "owner": "antonio",
        "tasks": [
            {"name": "Business plan v4", "done": True, "days": -25},
            {"name": "Valutazione pre-money", "done": False, "days": -3, "priority": "1"},
            {"name": "Setup piattaforma crowdfunding", "done": False, "days": 15},
            {"name": "Video pitch produzione", "done": False, "days": 20},
        ],
    },
    {
        "name": "Anuga 2026 Colonia",
        "tag": "Fiera",
        "date": "2026-10-15",
        "desc": "Fiera Anuga 11-15 ottobre 2026, lista 80 buyer prospect, agenda meeting, allestimento stand",
        "partner_search": None,
        "owner": "josefina",
        "tasks": [
            {"name": "Prenotazione stand", "done": True, "days": -60},
            {"name": "Lista buyer 80 prospect", "done": False, "days": -5, "priority": "1"},
            {"name": "Design allestimento", "done": False, "days": 30},
            {"name": "Agenda meeting buyer", "done": False, "days": 60},
            {"name": "Campionature fiera", "done": False, "days": 75},
        ],
    },
    {
        "name": "Linea Fluid launch",
        "tag": "Prodotto",
        "date": "2027-02-28",
        "desc": "Lancio linea pourable cream anhydrous 500ml dark glass, 40 referenze (Puri/Mediterranei/Fusion)",
        "partner_search": None,
        "owner": "antonio",
        "tasks": [
            {"name": "Formulazione base 3 linee", "done": True, "days": -40},
            {"name": "Test shelf life", "done": False, "days": 10},
            {"name": "Design etichette", "done": False, "days": 30},
            {"name": "Ordine bottiglie dark glass", "done": False, "days": 45},
        ],
    },
    {
        "name": "IFS recertification 2027",
        "tag": "Qualità",
        "date": "2027-01-31",
        "desc": "Audit IFS gennaio 2027, manuale HACCP v3, audit interni Q1, gap analysis pre-audit",
        "partner_search": None,
        "owner": "antonio",
        "tasks": [
            {"name": "Gap analysis pre-audit", "done": False, "days": 30},
            {"name": "Aggiornamento manuale HACCP v3", "done": False, "days": 60},
            {"name": "Audit interno Q4", "done": False, "days": 90},
            {"name": "Azioni correttive", "done": False, "days": 120},
        ],
    },
    {
        "name": "Halal renewal 2026",
        "tag": "Qualità",
        "date": "2026-11-30",
        "desc": "Rinnovo certificazione Halal annuale, ente certificatore",
        "partner_search": None,
        "owner": "antonio",
        "tasks": [
            {"name": "Raccolta documentazione", "done": True, "days": -10},
            {"name": "Invio domanda rinnovo", "done": False, "days": 5},
            {"name": "Audit on-site", "done": False, "days": 30},
        ],
    },
    {
        "name": "Onboarding Whole Foods Usa",
        "tag": "Export",
        "date": "2027-03-31",
        "desc": "Onboarding cliente Whole Foods USA, listino 2027, schede tecniche EN, Loi, certificazioni gluten-free statement",
        "partner_search": "Whole Foods",
        "owner": "josefina",
        "tasks": [
            {"name": "Listino 2027 USD", "done": True, "days": -15},
            {"name": "Schede tecniche EN", "done": False, "days": -2, "priority": "1"},
            {"name": "Gluten-free statement", "done": False, "days": 10},
            {"name": "Loi Whole Foods", "done": False, "days": 30},
            {"name": "Prima spedizione campioni", "done": False, "days": 45},
        ],
    },
]

_OWNER_MAP = {
    "antonio": "antonio@casafolino.com",
    "josefina": "josefina.lazzaro@casafolino.com",
    "maria": "martina.sinopoli@casafolino.com",  # fallback
}


def seed_projects(env):
    """Create 8 CasaFolino projects with tasks. Idempotent."""
    Project = env["project.project"]
    Task = env["project.task"]
    Tag = env["project.tags"]
    User = env["res.users"]
    Partner = env["res.partner"]

    today = date.today()

    for proj_data in _PROJECTS:
        # Check idempotency
        existing = Project.search([("name", "=", proj_data["name"])], limit=1)
        if existing:
            _logger.info("Project '%s' already exists, skipping", proj_data["name"])
            continue

        # Find tag
        tag = Tag.search([("name", "=", proj_data["tag"])], limit=1)
        tag_ids = [(4, tag.id)] if tag else []

        # Find partner
        partner_id = False
        if proj_data.get("partner_search"):
            partner = Partner.search(
                [("name", "ilike", proj_data["partner_search"])], limit=1
            )
            if partner:
                partner_id = partner.id

        # Find owner
        owner_login = _OWNER_MAP.get(proj_data["owner"], "antonio@casafolino.com")
        owner = User.search([("login", "=", owner_login)], limit=1)
        user_id = owner.id if owner else env.uid

        # Create project
        project = Project.create({
            "name": proj_data["name"],
            "privacy_visibility": "employees",
            "tag_ids": tag_ids,
            "date_start": today - timedelta(days=60),
            "date": proj_data["date"],
            "description": proj_data["desc"],
            "partner_id": partner_id,
            "user_id": user_id,
            "active": True,
        })
        _logger.info("Created project: %s (id=%s)", proj_data["name"], project.id)

        # Get task stages for this project
        # In Odoo 18, new projects get default stages
        # Find "done" stage (fold=True) and "in progress" stage
        stages = env["project.task.type"].search([
            ("project_ids", "in", project.id),
        ], order="sequence")

        done_stage = None
        progress_stage = None
        new_stage = None
        for s in stages:
            s_name = (s.name or "").lower() if isinstance(s.name, str) else ""
            if not s_name and hasattr(s, 'name'):
                # Handle translated name
                try:
                    s_name = str(s.name).lower()
                except Exception:
                    s_name = ""
            if s.fold:
                done_stage = s
            elif not new_stage:
                new_stage = s
            elif not progress_stage:
                progress_stage = s

        if not new_stage and stages:
            new_stage = stages[0]
        if not progress_stage and stages and len(stages) > 1:
            progress_stage = stages[1]

        # Create tasks
        for task_data in proj_data["tasks"]:
            deadline = today + timedelta(days=task_data["days"])
            stage = done_stage if task_data.get("done") and done_stage else (
                progress_stage if task_data["days"] < 15 and progress_stage else new_stage
            )

            task_vals = {
                "name": task_data["name"],
                "project_id": project.id,
                "date_deadline": deadline,
                "user_ids": [(4, user_id)],
                "priority": task_data.get("priority", "0"),
            }
            if stage:
                task_vals["stage_id"] = stage.id

            Task.create(task_vals)

        _logger.info("Created %d tasks for project '%s'", len(proj_data["tasks"]), proj_data["name"])

    env.cr.commit()
