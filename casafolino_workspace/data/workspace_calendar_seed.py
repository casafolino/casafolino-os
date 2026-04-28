# -*- coding: utf-8 -*-
"""Seed realistic calendar events for workspace demo."""
import logging
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)

_EVENTS = [
    {"name": "Stand-up team", "hour": 9, "dur": 30, "day_offset": 0, "type": "team", "attendees": ["antonio", "martina", "josefina"]},
    {"name": "Call Hoffmann Rewe - listino 2027", "hour": 10, "dur": 60, "day_offset": 0, "type": "buyer", "attendees": ["antonio", "josefina"]},
    {"name": "Review LOI D'Addezio", "hour": 14, "dur": 45, "day_offset": 0, "type": "deal", "attendees": ["antonio"]},
    {"name": "Sync produzione Lamezia", "hour": 16, "dur": 30, "day_offset": 0, "type": "team", "attendees": ["antonio", "martina"]},
    {"name": "Stand-up team", "hour": 9, "dur": 30, "day_offset": 1, "type": "team", "attendees": ["antonio", "martina", "josefina"]},
    {"name": "Call Mike Carson Whole Foods", "hour": 15, "dur": 60, "day_offset": 1, "type": "buyer", "attendees": ["antonio", "josefina"]},
    {"name": "Board prep crowdfunding", "hour": 11, "dur": 90, "day_offset": 1, "type": "investor", "attendees": ["antonio"]},
    {"name": "Stand-up team", "hour": 9, "dur": 30, "day_offset": 2, "type": "team", "attendees": ["antonio", "martina", "josefina"]},
    {"name": "Halal audit prep", "hour": 10, "dur": 60, "day_offset": 2, "type": "team", "attendees": ["antonio"]},
    {"name": "Anuga stand design review", "hour": 14, "dur": 45, "day_offset": 2, "type": "team", "attendees": ["antonio", "josefina"]},
    {"name": "Fiera SIAL Canada planning", "hour": 16, "dur": 60, "day_offset": 3, "type": "buyer", "attendees": ["antonio", "josefina"]},
    {"name": "Investor call - pre-money valuation", "hour": 11, "dur": 60, "day_offset": 3, "type": "investor", "attendees": ["antonio"]},
    {"name": "Firma notaio preliminare capannone", "hour": 9, "dur": 120, "day_offset": 4, "type": "deal", "attendees": ["antonio"]},
    {"name": "Week review & planning", "hour": 15, "dur": 60, "day_offset": 4, "type": "team", "attendees": ["antonio", "martina", "josefina"]},
    # Past events (for history)
    {"name": "Call Aldi DE - campionatura", "hour": 10, "dur": 45, "day_offset": -1, "type": "buyer", "attendees": ["antonio", "josefina"]},
    {"name": "Stand-up team", "hour": 9, "dur": 30, "day_offset": -1, "type": "team", "attendees": ["antonio", "martina"]},
    {"name": "IFS gap analysis kick-off", "hour": 14, "dur": 60, "day_offset": -2, "type": "team", "attendees": ["antonio"]},
    {"name": "Linea Fluid taste test", "hour": 11, "dur": 90, "day_offset": -3, "type": "team", "attendees": ["antonio", "martina"]},
]

_USER_MAP = {
    "antonio": "antonio@casafolino.com",
    "josefina": "josefina.lazzaro@casafolino.com",
    "martina": "martina.sinopoli@casafolino.com",
}


def seed_calendar(env):
    """Create demo calendar events. Idempotent."""
    Event = env["calendar.event"]
    User = env["res.users"]

    today = date.today()
    # Check idempotency
    existing = Event.search([("name", "=", "Stand-up team"), ("start", ">=", str(today - timedelta(days=7)))], limit=1)
    if existing:
        _logger.info("Calendar events already seeded, skipping")
        return

    user_cache = {}
    for key, login in _USER_MAP.items():
        u = User.search([("login", "=", login)], limit=1)
        if u:
            user_cache[key] = u

    for ev in _EVENTS:
        target_date = today + timedelta(days=ev["day_offset"])
        start_dt = datetime(target_date.year, target_date.month, target_date.day, ev["hour"], 0)
        stop_dt = start_dt + timedelta(minutes=ev["dur"])

        partner_ids = []
        for att in ev.get("attendees", []):
            u = user_cache.get(att)
            if u:
                partner_ids.append((4, u.partner_id.id))

        Event.create({
            "name": ev["name"],
            "start": start_dt,
            "stop": stop_dt,
            "allday": False,
            "partner_ids": partner_ids,
            "user_id": user_cache.get("antonio", env.user).id,
        })

    _logger.info("Created %d calendar events", len(_EVENTS))
    env.cr.commit()
