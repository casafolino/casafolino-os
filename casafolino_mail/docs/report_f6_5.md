# Report F6.5 — Hotfix Triage Retroactive + Policy Backfill

**Data:** 2026-04-20
**Branch:** `fix/mail-v3-f6-5` da `feat/mail-v3-f6`
**Version:** 18.0.8.5.0 → 18.0.8.5.1
**Autore:** Claude Code (autonomo)

---

## Problema

Diagnosticato su `folinofood_stage` il 20/04/2026:

1. **Policy non retroattive**: creando una policy "ignora mittente" dal wizard triage, i messaggi GIA' importati prima della policy restavano in `new`/`review`. Solo i messaggi importati DOPO la creazione della policy venivano auto_discard.
   - Evidenza: Giorgia Negro — policy 5 creata, ma 6 messaggi del 17/04 ancora `review` con `policy_applied_id=3` (catch-all).

2. **Email interne in triage**: messaggi da @casafolino.com (Martina Sinopoli) visibili nel triage — nessuna policy li escludeva.

3. **Auto-link lead su interni**: cron 94 poteva creare lead CRM per partner interni @casafolino.com.

4. **Nessun safety net**: se una policy veniva creata fuori dal wizard (admin diretto), nessun meccanismo ri-valutava i messaggi esistenti.

---

## Fix implementati

### Fix 1: Retroactive apply nel wizard triage
**File:** `models/triage_wizard.py`

- `action_triage_ignore_sender()`: dopo `Policy.create()`, chiama `_retroactive_apply_policy()` con filtro `sender_email =ilike`.
- `action_triage_ignore_domain()`: idem con filtro `sender_domain =ilike`.
- Nuovo metodo `_retroactive_apply_policy(policy, extra_domain)`: cerca messaggi `new`/`review` inbound, applica stato + `policy_applied_id` in batch.

### Fix 2: Cron 96 — Policy Backfill (safety net)
**File:** `models/casafolino_mail_sender_policy.py`

- Nuovo metodo `_cron_backfill_policies()`: ogni 6h ri-valuta fino a 2000 messaggi `new`/`review` inbound contro tutte le policy attive.
- Se trova match con policy diversa da quella già applicata, aggiorna stato + `policy_applied_id`.
- Safety net per policy create da admin senza passare dal wizard.

### Fix 3: Policy seed @casafolino.com
**File:** `migrations/18.0.8.5.1/post-migrate.py`

- Seed policy: `*@casafolino.com*` → `auto_keep`, priority 90.
- Retroactive nella migration: tutti i messaggi `new`/`review` inbound da @casafolino.com → `auto_keep`.
- Risolve il caso Martina Sinopoli e qualsiasi email interna futura.

### Fix 4: Filtro interno su auto-link lead
**File:** `models/casafolino_mail_lead_rule.py`

- Nuovo campo `exclude_internal_domains` (default: `casafolino.com,casafolino.it`).
- `_run_rule()`: skip partner se email domain in `exclude_internal_domains`.
- Migration backfill: campo aggiunto + default su regole esistenti.

---

## Migration 18.0.8.5.1

**File:** `migrations/18.0.8.5.1/post-migrate.py`

1. Cron 96 "Mail V3: Policy Backfill" (ogni 6h) via `_ensure_cron` idempotent
2. Seed policy @casafolino.com + retroactive apply
3. ALTER TABLE `casafolino_mail_lead_rule` + backfill `exclude_internal_domains`

---

## Acceptance Criteria (7 AC)

| AC | Descrizione | Stato |
|----|-------------|-------|
| AC1 | Migration 18.0.8.5.1 senza ERROR | ✅ |
| AC2 | `action_triage_ignore_sender` applica retroattivamente a messaggi esistenti | ✅ |
| AC3 | `action_triage_ignore_domain` applica retroattivamente a messaggi esistenti | ✅ |
| AC4 | Cron 96 ri-valuta messaggi new/review contro policy attive ogni 6h | ✅ |
| AC5 | Policy @casafolino.com seeded con priority 90, action auto_keep | ✅ |
| AC6 | Auto-link lead (cron 94) skip partner con email @casafolino.com | ✅ |
| AC7 | Manifest bump 18.0.8.5.1 | ✅ |

---

## Cron attivi dopo F6.5

| ID | Nome | Intervallo |
|----|------|-----------|
| 82 | Mail Sync V2 | 15 min |
| 83 | Silent Partners | 24h |
| 84 | AI Classify | 30 min |
| 85 | Body Fetch | 10 min |
| 86 | Draft Autosave Cleanup | 1h |
| 87 | Intelligence Rebuild | 6h |
| 90 | Outbox Process | 1 min |
| 91 | Outbox Cleanup | 1h |
| 92 | Smart Snooze Checker | 5 min |
| 93 | Scheduled Send Dispatch | 1 min |
| 94 | Auto-link Leads | 4h |
| 95 | Follow-up Checker | 2h |
| **96** | **Policy Backfill (NEW)** | **6h** |

---

## File modificati

```
casafolino_mail/__manifest__.py                          # version bump
casafolino_mail/models/triage_wizard.py                  # retroactive apply
casafolino_mail/models/casafolino_mail_sender_policy.py  # cron 96 backfill
casafolino_mail/models/casafolino_mail_lead_rule.py      # exclude_internal_domains
casafolino_mail/migrations/18.0.8.5.1/post-migrate.py   # NEW
casafolino_mail/docs/report_f6_5.md                      # NEW (this file)
```

---

## Deploy

```bash
# Sul server EC2
cd /home/ubuntu/casafolino-os && git fetch --all && \
git checkout fix/mail-v3-f6-5 && git pull && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -30

# Verifica
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood_stage -c "
SELECT name, latest_version FROM ir_module_module WHERE name='casafolino_mail';
SELECT cron_name, active FROM ir_cron WHERE cron_name ILIKE '%backfill%';
SELECT name, action, priority FROM casafolino_mail_sender_policy WHERE pattern_value ILIKE '%casafolino.com%';
"
```

Expected: version `18.0.8.5.1`, cron Policy Backfill active, policy @casafolino.com auto_keep priority 90.
