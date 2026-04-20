# Merge Report — F2.1 + F3 → feat/mail-v3-merged
Date: 2026-04-20
Branch: feat/mail-v3-merged
Version: 18.0.8.2.0

## Strategia merge

Base: `feat/mail-v3-f2.1` (F2 MVP + F2.1 hotfix)
Merged: `feat/mail-v3-f3` (Intelligence + Intent + Sync + Outbox)
Metodo: `git merge --no-ff` con risoluzione manuale conflitti.

## Conflitti risolti (4 file)

### 1. `__manifest__.py`
- **Conflitto**: version (18.0.8.0.1 vs 18.0.8.1.0) + summary
- **Risoluzione**: version = 18.0.8.2.0 (max +1). Summary da F2 (piu descrittivo). Depends e data merged (F2 ha V3 assets/groups/views, F3 ha intelligence_views.xml — entrambi presenti).

### 2. `models/__init__.py`
- **Conflitto**: F2 aggiunge thread/draft/signature/intelligence/res_users. F3 aggiunge intelligence/flag_sync/outbox.
- **Risoluzione**: tutti presenti. Intelligence import unico (F2 gia lo importa). flag_sync e outbox aggiunti dopo.

### 3. `models/casafolino_partner_intelligence.py`
- **Conflitto**: F2 ha stub (365 righe), F3 ha full NBA engine (711 righe).
- **Risoluzione**: F3 come base (NBA engine completo), con miglioramenti F2 integrati:
  - Emoji nei tier labels (🔥 Hot, 🔶 Warm, 💼 Active, 🧊 Cold, ⚫ Dormant)
  - `math.log10` per revenue (curva piu precisa vs step function)
  - `_get_partner_ids()` helper per company hierarchy (parent + children)
  - `amount_untaxed_signed` (F2) invece di `amount_total_signed` (F3)
  - `try/except` wrapping su tutte le query cross-module
  - `sudo()` su lead/order/invoice queries

### 4. `security/ir.model.access.csv`
- **Conflitto**: F2 usa V3 groups per intelligence, F3 usa base groups + outbox.
- **Risoluzione**: F2 groups per thread/draft/signature/intelligence (V3 group system). Outbox con base groups (non V3-specific).

## Migration ordering

- `8.0.0/post-migrate.py` (F2) — thread backfill, cron 88/90, beta users, indexes
- `18.0.8.2.0/post-migrate.py` (F3, rinominato da 18.0.8.1.0) — intelligence crons, flag sync, outbox, config params, initial rebuild

Ordine corretto: Odoo esegue migrations in ordine di version string. 8.0.0 < 18.0.8.2.0.

## Auto-merge riusciti (senza conflitti)

- `casafolino_mail_account.py` — F2 aggiunge _smtp_send + OWL API. F3 aggiunge _detect_intent call nel fetch. Nessun overlap.
- `casafolino_mail_message_staging.py` — F2 aggiunge V3 fields (thread_id, is_read, is_starred, etc). F3 aggiunge intent_detected + imap_flags_synced + _detect_intent(). Merge automatico OK.

## Contenuto finale branch

### Da F2/F2.1 (14 commit)
- Core V3 models: thread, draft, signature
- OWL frontend: 6 componenti + templates + SCSS
- Controllers + API endpoints
- SMTP send con retry
- Security groups + record rules (8 rules)
- Migration 8.0.0 (thread backfill, cron)
- Data seeds + menus V3

### Da F3 (8 commit)
- Partner Intelligence con 20 NBA rules + LLM fallback
- Intent Detection trilingue IT/EN/DE (11 intenti)
- IMAP Flag Sync bidirezionale
- Async SMTP Queue (outbox)
- Intelligence + Outbox views
- Migration 18.0.8.2.0

### Integrazione
- Intelligence model: F3 NBA engine completo + F2 miglioramenti (hierarchy, log scale, emoji)
- ACL: V3 groups per modelli V3, base groups per outbox
- Manifest: version 18.0.8.2.0, tutte le dipendenze, tutti gli assets
