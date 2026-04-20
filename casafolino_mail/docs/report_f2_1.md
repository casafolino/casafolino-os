# F2.1 Report — UI Hotfix
Date: 2026-04-19
Commits: 4
Push: feat/mail-v3-f2.1

## Completati

- AC1: Branch `feat/mail-v3-f2.1` creato da `feat/mail-v3-f2`
- AC2: `security/mail_v3_rules.xml` aggiornato con 8 rules (account_own, account_admin, message_own, message_admin, draft_own, draft_admin, thread_own, thread_admin)
- AC3: Rule draft_own + draft_admin presenti e corrette
- AC4: Controller `/accounts/summary` usa solo `search([('active','=',True)])` — record rules filtrano automaticamente (admin=3 account, altri=1)
- AC5: Controller `/threads/list` accetta `account_ids=None` — nessun filtro manuale, record rules filtrano
- AC6: Controller `/threads/list` ritorna hotness_score + hotness_tier + hotness_emoji (invariato da F2, gia funzionante)
- AC7: Manifest bump 18.0.8.0.0 → 18.0.8.0.1
- AC8: Convention-commits pushati su `feat/mail-v3-f2.1`
- AC9: Report prodotto

## Note

Root cause del bug: doppio problema.

1. **Mancavano record rules su `casafolino.mail.account`**. Il modello account non aveva nessuna rule V3, quindi il controller faceva filtro manuale con `responsible_user_id = uid`. Per l'admin, il codice faceva una seconda query senza filtro, ma le record rules base di Odoo potevano interferire.

2. **Controller threads/list faceva filtro manuale**. Quando `account_ids=None`, il controller cercava esplicitamente gli account con `responsible_user_id = uid` e poi filtrava i thread su quegli account. Per l'admin, questo significava vedere solo i thread del proprio account (1 su 3). Ora il controller non filtra — le record rules (con admin bypass `[(1,'=',1)]`) gestiscono tutto.

Le rule disattivate manualmente in PROD (`UPDATE ir_rule SET active=false`) verranno riattivate automaticamente dal `-u casafolino_mail` perche l'XML con `noupdate="1"` aggiorna solo se il record non esiste o se l'xml_id e cambiato. Se non si riattivano, eseguire:

```sql
UPDATE ir_rule SET active=true WHERE name ILIKE '%Mail V3%';
```

## Come testare

Dopo deploy + refresh browser (Cmd+Shift+R):

1. Antonio (admin) vede 3 account in sidebar: Antonio + Martina + Josefina
2. Click "Tutti" mostra ~361 thread
3. Click account singolo filtra per quell'account
4. Click thread carica reading pane + sidebar 360
5. Josefina/Martina vedono solo il proprio account e i propri thread

## Commits

- `c69197a` fix(mail-v3): record rules — add account rules + draft admin bypass
- `b022cd5` fix(mail-v3): controllers rely on record rules for visibility
- `7cc2831` chore(mail-v3): bump manifest 18.0.8.0.0 → 18.0.8.0.1
- `(this)` docs(mail-v3): F2.1 hotfix report
