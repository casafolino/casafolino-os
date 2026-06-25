# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def _ensure_env(env):
    if hasattr(env, "registry"):
        return env
    return api.Environment(env, SUPERUSER_ID, {})


def _ensure_server_action(env, name, model_name, code):
    model = env["ir.model"]._get(model_name)
    action = env["ir.actions.server"].sudo().search([
        ("name", "=", name),
        ("model_id", "=", model.id),
    ], limit=1)
    if action:
        action.write({"code": code, "state": "code"})
        return action
    return env["ir.actions.server"].sudo().create({
        "name": name,
        "model_id": model.id,
        "state": "code",
        "code": code,
    })


def _ensure_cron(env, name, action, interval_number, interval_type):
    cron = env["ir.cron"].sudo().search([
        ("cron_name", "=", name),
    ], limit=1)
    vals = {
        "cron_name": name,
        "ir_actions_server_id": action.id,
        "interval_number": interval_number,
        "interval_type": interval_type,
        "active": True,
    }
    if cron:
        cron.write(vals)
        return cron
    return env["ir.cron"].sudo().create(vals)


def post_init_hook(env):
    env = _ensure_env(env)
    ICP = env["ir.config_parameter"].sudo()
    ICP.set_param("cf_haccp.enforce_receipt_gate", "1")
    ICP.set_param("cf_haccp.enforce_production_gate", "1")

    daily_action = _ensure_server_action(
        env,
        "HACCP - Reminder registri giornalieri",
        "cf.haccp.reminder",
        "model._send_daily_reminders()",
    )
    _ensure_cron(
        env,
        "HACCP - Reminder registri giornalieri",
        daily_action,
        1,
        "days",
    )

    weekly_action = _ensure_server_action(
        env,
        "HACCP - Reminder scadenze documenti e calibrazioni",
        "cf.haccp.reminder",
        "model._send_weekly_document_reminders()",
    )
    _ensure_cron(
        env,
        "HACCP - Reminder scadenze documenti e calibrazioni",
        weekly_action,
        1,
        "weeks",
    )
