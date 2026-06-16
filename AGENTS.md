# CasaFolino — AGENTS (Canonical instructions)

## Scopo
Questa è la fonte canonica condivisa tra Claude Code e Codex per tutte le regole universali del progetto: Odoo 18 rules, deploy flow, architettura, struttura repo, naming & palette UI, e riferimenti per la riconciliazione bancaria. Evita duplicazione e drift; `CLAUDE.md` e altri file agent-specific importano o rimandano qui.

---

## Progetto
Modulo Odoo 18 custom per CasaFolino Srls (azienda food italiana).
Stack: Odoo 18 Enterprise, Docker, PostgreSQL 15, AWS EC2.

---

## Indice veloce
- Canonical Odoo 18 rules
- Repo & structure
- Bank reconciliation (where/what)
- Naming / Palette / UI rules
- Deploy flow
- Useful commands & references

---

## Canonical Odoo 18 rules — (MAI VIOLARE)
1) Event handlers nei template XML
- Evita arrow functions con blocco `{}` nelle espressioni t-on-*
- Usa sempre metodi del componente (es. `onSelectChange`, `onInputChange`)

2) CSS — niente import esterni
- Non importare risorse esterne (es. Google Fonts) nei CSS degli assets; usare font di sistema o font già in Odoo.

3) RPC calls nel JS
- Importare ed usare `rpc` da `@web/core/network/rpc` (no shim `web.rpc` o `useService('rpc')` legacy).

4) Views XML — attributi condizionali
- Non usare `attrs=`: usare `invisible="state == 'draft'"` o analoghi.

5) Expressions — invisible/readonly
- Non usare parentesi tonde nelle expressions XML (es. `invisible="state == 'draft'"`).

6) Assets nel manifest
- Registrare assets per il backend con `web.assets_backend` (non `web.assets_web` per backend).

7) Menus XML — ordine dichiarazione
- Dichiarare `record`/`action` PRIMA del `menuitem` che le usa.

8) Conflitti `ir_model_data`
- Se appare l'errore su record di modello differente, rimuovere entry errate da `ir_model_data` come indicato nel repo.

---

## Repo & module structure (canonical)
Esempio modulo:
```
casafolino_mail/
├── __manifest__.py
├── models/
├── static/src/
├── views/
└── security/
```
Per le regole di naming e struttura consultare `.planning/codebase/STRUCTURE.md` e `ARCHITECTURE.md`.

---

## Bank reconciliation (stato riconciliazione bancaria)
- Gli script di import e riconciliazione sono sotto `scripts/` (es. `scripts/import_bank_statements.py` e `scripts/reconcile_step2_auto.py`).
- Policy: le riconciliazioni automatizzate devono usare i modelli di riconciliazione Odoo 18; eventuali eccezioni devono essere documentate in `.planning/codebase/INTEGRATIONS.md`.

Riferimenti:
- `scripts/import_bank_statements.py`
- `.planning/codebase/INTEGRATIONS.md`

---

## Naming / Palette / UI rules
- Palette CasaFolino (valori canonici):
    - Accent primario: `#5A6E3A`
    - Accent dark: `#3d4d28`
    - Accent light: `rgba(90,110,58,0.1)`
- Font: sistema sans-serif (no Google Fonts importati).
- UI naming: segui i pattern esistenti nei file `static/src/scss` e nei brief in `casafolino_mail/docs/`.

Riferimenti:
- `casafolino_mail/docs/report_f8.md`
- `casafolino_crm_export/static/src/scss/` (palette notes)

---

## Deploy flow (canonical)
- Keep a reproducible `deploy.sh` per host; valore host/target non committare come secret in chiaro (vedi sezione sicurezza).
- Esempio (da mantenere come regola):
```bash
# Uso tipico (stage)
# docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http
# Pulizia cache assets
# docker exec odoo-db psql -U odoo -d folinofood_stage -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';"
# Restart
# docker restart odoo-app
```

NOTE: mantenere il valore host/indirizzo di deploy in variabile d'ambiente (es. `DEPLOY_HOST`) e NON in file di istruzioni committati.

---

## Database
- Stage DB: `folinofood_stage`
- Prod DB: `folinofood` (non toccare senza autorizzazione esplicita)

---

## Useful commands & quick references
- Aggiorna modulo:
    `docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http`
- Pulisci asset cache:
    `docker exec odoo-db psql -U odoo -d folinofood_stage -c "DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';"`
- Restart:
    `docker restart odoo-app`

---

## References (local)
- `.planning/codebase/STRUCTURE.md`
- `scripts/import_bank_statements.py`
- `casafolino_mail/docs/report_f8.md`

