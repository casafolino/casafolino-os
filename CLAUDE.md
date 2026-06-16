@AGENTS.md

## Claude-specific

- **Formato brief:** usare il formato GSD brief (conciso, background, acceptance criteria, UAT).
- **Skill da usare:** `casafolino-odoo-deploy`, `casafolino-mail-v2`.
- **Plan mode convention:** in `Plan mode` i deploy proposti possono essere Auto-accepted per deploy su `stage` quando il piano è completo e i test sono verdi; per deploy su `prod` richiedere confirm human explicita (policy di sicurezza).

Note: tutte le regole universali, incluse Odoo 18 rules, deploy flow, naming e palette UI, sono canoniche in `AGENTS.md`.
