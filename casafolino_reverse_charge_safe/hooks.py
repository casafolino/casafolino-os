def _post_init_reverse_charge_action(env):
    """Attach the safe reverse-charge procedure to legacy manual actions."""
    action_name = "Registra e invia integrazione reverse charge"
    action_code = "action = records.action_cf_reverse_charge_register_and_send()"
    legacy_actions = env["ir.actions.server"].search([
        ("model_id.model", "=", "account.move"),
        ("state", "=", "code"),
        ("code", "ilike", "action_l10n_it_edi_send"),
    ])
    for action in legacy_actions:
        action.write({
            "code": action_code,
        })

    safe_actions = env["ir.actions.server"].search([
        ("model_id.model", "=", "account.move"),
        ("state", "=", "code"),
        ("code", "=", action_code),
    ])
    for action in safe_actions:
        action.with_context(lang="en_US").write({"name": action_name})
        action.with_context(lang="it_IT").write({"name": action_name})
