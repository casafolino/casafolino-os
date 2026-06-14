# Brief F6.5 rev2 — Completamento Fix Triage + Filtro F6

**Formato:** GSD — **MODALITÀ AUTONOMA TOTALE**
**Owner:** Antonio Folino
**Reference:** `diagnostica_triage.md` + commit `4aca931`
**Base:** `fix/mail-v3-f6-5` (HEAD `4aca931`, locale sul Mac, NON pushato)
**Target:** `casafolino_mail` 18.0.8.5.0 → 18.0.8.5.1
**Tempo stimato:** 30-45 min autonomi
**Tipo:** Completamento hotfix (3 fix UI + 1 filtro F6)

---

## 🚀 COME LANCIARE

**Sul Mac (terminale nuovo):**

```bash
cd ~/casafolino-os
git checkout fix/mail-v3-f6-5
git status   # verifica: devi essere su fix/mail-v3-f6-5, HEAD 4aca931
claude --dangerously-skip-permissions
```

Poi incolla questo brief dentro Code e scrivi "Vai".

---

## 📋 STATO ATTUALE DEL BRANCH (commit 4aca931 già fatto)

Questo commit contiene già:
- ✅ `_retroactive_apply_policy` helper nel wizard
- ✅ `action_triage_ignore_sender` chiama retroactive apply
- ✅ `action_triage_ignore_domain` chiama retroactive apply
- ✅ Cron 96 Policy Backfill (2h interval)
- ✅ Policy seed `*@casafolino.com → auto_keep` in migration
- ✅ Migration 18.0.8.5.1 post-migrate

**Manca ancora:**
- ❌ Fix `_open_next_orphan` (bug: Skip torna sullo stesso partner)
- ❌ Nuovo bottone "✅ Tieni contatto" (UX gap)
- ❌ Filtro F6 Auto-link Leads exclude discarded/ignored senders
- ❌ Conclusione notification Skip quando queue vuota (UX polish)
- ❌ Report f6_5.md

**NON toccare quello che già c'è.** Estendi solo.

---

## ⚠️ 4 REGOLE CRITICHE

1. **MAI fermarsi** — eccezioni: data loss prod, credenziali mancanti
2. **Defaults automatici**: naming coerente con pattern esistenti, IT pro, skip+annota bug pre-esistenti
3. **Auto-escape 30 min** → commit `wip`, skip, avanti
4. **Commit ogni task + push finale**

---

## 1. Obiettivo

Chiudere 3 bug UX del wizard Triage Orfano + proteggere F6 Auto-link Leads dai sender bloccati. Garantire zero regressioni rispetto al commit 4aca931.

**Definition of Done:**

Antonio clicca "Skip (decidi dopo)" su Eleonora Sala → passa immediatamente al prossimo orfano diverso (se c'è) oppure vede notifica "Triage completo" + wizard si chiude. Antonio clicca "✅ Tieni contatto" → crea decisione `kept`, partner non riappare mai più, passa al prossimo. Cron 94 F6 Auto-link non crea mai `crm.lead` per partner con decisione `ignored_sender` o policy `auto_discard` attiva.

---

## 2. Contesto dalla diagnostica

**Evidenza DB:**
- `casafolino_mail_orphan_partner` → 28 record in queue
- `casafolino_mail_sender_decision` → 0 decisioni attive
- Test UI su Eleonora Sala: Skip non avanza perché `_open_next_orphan` non esclude il partner corrente

**Evidenza codice** (`triage_wizard.py`):
```python
@api.model
def _open_next_orphan(self):
    triaged_ids = Decision.search([('active', '=', True)]).mapped('partner_id').ids
    next_orphan = Orphan.search([
        ('partner_id', 'not in', triaged_ids)  # ← BUG: non esclude self.partner_id
    ], limit=1)
```

Se il current partner ha 0 decisioni attive (tipico quando si chiama Skip senza creare policy), `next_orphan` restituisce lo stesso partner.

---

## 3. Scope IN — 4 deliverable + report

### 3.1 Fix `_open_next_orphan` — escludere current partner (5 min)

File: `casafolino_mail/models/triage_wizard.py`

Il metodo `_open_next_orphan` è `@api.model` quindi non ha `self.partner_id` automaticamente. Serve passare il current_id esplicitamente.

**Modifica firma + chiamate:**

```python
@api.model
def _open_next_orphan(self, exclude_partner_ids=None):
    """Trova prossimo orfano non triagiato, escludendo opzionalmente partner_ids.
    
    Args:
        exclude_partner_ids: list of partner IDs to exclude (usually the current one)
    """
    Orphan = self.env['casafolino.mail.orphan.partner']
    Decision = self.env['casafolino.mail.sender.decision']
    
    triaged_ids = Decision.search([('active', '=', True)]).mapped('partner_id').ids
    exclude_ids = list(set(triaged_ids + (exclude_partner_ids or [])))
    
    next_orphan = Orphan.search([
        ('partner_id', 'not in', exclude_ids)
    ], limit=1)
    
    if not next_orphan:
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Triage completo!',
                'message': 'Tutti gli orfani sono stati triagiati.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},  # ← chiude il wizard corrente
            },
        }
    
    # ... resto del metodo invariato (crea wizard, apre form)
```

**Update chiamate esistenti:** tutti i callers (`action_triage_skip`, `action_triage_lead`, `action_triage_assign`, `action_triage_snippet`, `action_triage_ignore_sender`, `action_triage_ignore_domain`) devono passare `exclude_partner_ids=[self.partner_id.id]`:

```python
def action_triage_skip(self):
    self.ensure_one()
    return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])
```

Applica lo stesso pattern a tutti i `return self._open_next_orphan()` nei metodi action del wizard.

### 3.2 Nuovo bottone "✅ Tieni contatto" (10 min)

**Decision type nuovo** — verifica prima che esista nel selector `decision`. File probabile: `models/casafolino_mail_sender_decision.py`

Se il campo `decision` è Selection con valori tipo `[('ignored_sender',...), ('ignored_domain',...), ('lead_created',...)]`, aggiungi `('kept', 'Tenuto (valido, no policy)')`.

**Nuovo metodo nel wizard:**

```python
def action_triage_keep(self):
    """Tieni partner come contatto valido, nessuna policy, nessun discard.
    Crea decisione 'kept' per rimuoverlo dalla queue."""
    self.ensure_one()
    self._create_decision('kept', notes='Contatto valido, tenuto da triage orfano')
    return self._open_next_orphan(exclude_partner_ids=[self.partner_id.id])
```

**View XML** — in `views/triage_wizard_views.xml` o equivalente (grep per `action_triage_lead` ti porta al file). Aggiungi il bottone nella sezione "Azioni positive" accanto agli altri 3:

```xml
<button name="action_triage_keep" 
        string="✅ Tieni contatto" 
        type="object" 
        class="btn btn-info btn-lg o_triage_btn" 
        style="padding: 16px 32px; font-size: 1.1em; min-width: 180px;"/>
```

Posizione suggerita: PRIMA di "Crea Lead", perché è l'azione più soft ("questo partner va bene così com'è").

### 3.3 Filtro F6 Auto-link Leads — exclude discarded/ignored (10 min)

File: `casafolino_mail/models/casafolino_mail_lead_rule.py` (creato in F6, commit `b9b512d`).

Nel metodo che esegue la rule (cerca `_execute_rule` o `_find_candidates` o `action_run_rule`), aggiungi **pre-filter** per escludere:

1. Thread dove il partner ha una decisione `ignored_sender` o `ignored_domain` attiva
2. Thread dove il sender ha una policy `auto_discard` attiva

**Implementazione pragmatica:**

```python
def _get_excluded_partner_ids(self):
    """Partner esclusi da auto-link: hanno decisione ignore o policy discard."""
    # Partner con decisione 'ignored_sender' o 'ignored_domain'
    Decision = self.env['casafolino.mail.sender.decision']
    ignored_decisions = Decision.search([
        ('active', '=', True),
        ('decision', 'in', ['ignored_sender', 'ignored_domain']),
    ])
    ignored_ids = ignored_decisions.mapped('partner_id').ids
    
    # Partner con email matching policy discard attiva
    Policy = self.env['casafolino.mail.sender_policy']
    discard_policies = Policy.search([
        ('active', '=', True),
        ('action', '=', 'auto_discard'),
    ])
    
    discard_ids = []
    if discard_policies:
        # Per ciascuna policy, trova partner matching
        Partner = self.env['res.partner']
        for policy in discard_policies:
            if policy.pattern_type == 'email':
                pattern = policy.pattern_value.replace('*', '%')
                partners = Partner.search([('email', '=ilike', pattern)])
                discard_ids.extend(partners.ids)
            elif policy.pattern_type == 'domain':
                # Pattern tipico: *@domain.com* → estrai dominio
                val = policy.pattern_value.strip('*')
                if '@' in val:
                    domain = val.split('@')[-1].strip('*')
                else:
                    domain = val.strip('*')
                if domain:
                    partners = Partner.search([('email', '=ilike', f'%@%{domain}%')])
                    discard_ids.extend(partners.ids)
    
    return list(set(ignored_ids + discard_ids))
```

**Poi nel metodo execute rule**, prima della search candidati:

```python
excluded_ids = self._get_excluded_partner_ids()
domain_candidates.append(('partner_id', 'not in', excluded_ids))
```

**Log:**
```python
_logger.info('[cron 94] Rule %s: %s partners excluded (ignored/discarded)',
             rule.name, len(excluded_ids))
```

### 3.4 UX polish notification (3 min)

Nel `_open_next_orphan`, quando queue vuota, la notification deve chiudere il wizard corrente. Usa `next` param:

```python
return {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Triage completo!',
        'message': f'Tutti gli orfani triagiati. ({triaged_count} decisioni attive)',
        'type': 'success',
        'sticky': False,
        'next': {'type': 'ir.actions.act_window_close'},  # ← chiude wizard
    },
}
```

Dove `triaged_count = len(triaged_ids)`. Serve all'utente per confermare "sì, queue davvero vuota".

### 3.5 Report f6_5.md (5 min)

File: `casafolino_mail/docs/report_f6_5.md`

```markdown
# Report F6.5 — Hotfix Sender Policy + Triage UX

**Branch:** fix/mail-v3-f6-5
**Version:** 18.0.8.5.0 → 18.0.8.5.1
**Data:** 2026-04-20
**Commits:** {elencare quelli fatti}

## Fix applicati

### Da commit 4aca931 (già presenti)
- [x] `_retroactive_apply_policy` helper wizard
- [x] `action_triage_ignore_sender` retroactive apply
- [x] `action_triage_ignore_domain` retroactive apply
- [x] Cron 96 Policy Backfill (2h)
- [x] Policy seed `*@casafolino.com → auto_keep`

### Aggiunti in questa sessione
- [x] Fix `_open_next_orphan` — esclude current partner
- [x] Nuovo bottone "✅ Tieni contatto" → decisione 'kept'
- [x] Filtro F6 Auto-link Leads — exclude ignored/discarded partners
- [x] UX notification chiude wizard quando queue vuota

## Acceptance Criteria

- AC1: Skip su partner → passa a partner diverso (non ritorna stesso)
- AC2: Bottone Tieni crea decisione 'kept' → partner non riappare
- AC3: Cron 94 F6 Auto-link esclude partner con decisione ignored/domain o policy discard
- AC4: Queue vuota → notification + wizard chiuso
- AC5: Retroactive apply su Ignore Sender funziona (inherited da 4aca931)

## Deploy path

Sul Mac:
- git push origin fix/mail-v3-f6-5

Sul server EC2:
- cd /home/ubuntu/casafolino-os
- git fetch && git checkout fix/mail-v3-f6-5 && git pull
- sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/
- docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tail -80
- {se stage OK} → prod con backup preventivo

## Verifica post-deploy

Query utili:
- SELECT COUNT(*) FROM casafolino_mail_sender_decision WHERE decision='kept';
- SELECT COUNT(*) FROM casafolino_mail_sender_policy;
- SELECT * FROM ir_cron WHERE id=96;
- SELECT COUNT(*) FROM casafolino_mail_message WHERE sender_domain='casafolino.com' AND state='auto_keep';

## Raccomandazioni F6.6 (se servirà)

- Counter reale orfani totali nel wizard (oggi mostra 1/1 sempre)
- Search bar dentro wizard per cercare partner specifico
- Bulk actions: "Ignora tutti i .ru" / "Ignora tutti noreply@*"
```

---

## 4. Scope OUT

- ❌ NO modifiche a commit 4aca931 (retroactive apply + cron 96 + seed)
- ❌ NO nuove tabelle
- ❌ NO cambio schema esistente
- ❌ NO toccare F6 cron 95 (Follow-up)
- ❌ NO modifiche Mail V3 UI (client principale)
- ❌ NO refactor wizard (solo add metodi/fix chiamate)

---

## 5. Vincoli Odoo 18

- `@api.model` per metodi senza recordset (es. `_open_next_orphan`)
- `self.ensure_one()` in metodi action con record specifico
- `sudo()` per search cross-user (Decision/Policy)
- `_create_decision` helper già esiste in wizard — riusalo per `kept`
- View XML: `<button>` con `type="object"` — NO JS custom

---

## 6. Acceptance Criteria (5 AC)

- **AC1** Upgrade modulo 18.0.8.5.0 → 18.0.8.5.1 senza ERROR
- **AC2** Click "Skip" su partner X → apre wizard su partner Y diverso (o notifica se queue vuota)
- **AC3** Click "✅ Tieni contatto" → crea decisione kept, partner non riappare in queue
- **AC4** Cron 94 Auto-link: log mostra "N partners excluded" > 0 dopo primo giro (partner con decisione ignored)
- **AC5** Queue vuota → notifica success + wizard si chiude (non resta bloccato su ultimo partner)

---

## 7. Deploy path

**Sul Mac (dopo commit + push):**

```bash
cd ~/casafolino-os && \
git push origin fix/mail-v3-f6-5
```

**Sul server EC2 (ssh ubuntu@51.44.170.55):**

```bash
# 1. Backup preventivo
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo -Fc folinofood_stage > /tmp/folinofood_stage_before_f6_5_$(date +%Y%m%d_%H%M%S).dump

# 2. Checkout branch + sync codice
cd /home/ubuntu/casafolino-os && \
git fetch --all && \
git checkout fix/mail-v3-f6-5 && \
git pull && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/

# 3. Upgrade stage
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f6_5_stage.log | tail -60

# 4. Check errori
grep -E "ERROR|CRITICAL|Traceback" /tmp/f6_5_stage.log | head

# 5. Test UI 5 min su stage (vedi test post-deploy sotto)

# 6. Se tutto OK → prod
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo -Fc folinofood > /tmp/folinofood_before_f6_5_$(date +%Y%m%d_%H%M%S).dump

docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f6_5_prod.log | tail -60 && \
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "DELETE FROM ir_attachment WHERE name LIKE '%web.assets%';" && \
docker restart odoo-app
```

---

## 8. Test post-deploy stage (5 min)

1. Login su `https://erp.casafolino.com/web?db=folinofood_stage` in incognito
2. Mail CRM → Inbox Triage (o "Triage Orfano", menu principale)
3. **Test Skip**: click "Skip (decidi dopo)" → deve passare a partner diverso o mostrare notifica se queue vuota
4. **Test Tieni**: click "✅ Tieni contatto" su un partner valido (es. Eleonora Sala) → passa al prossimo
5. **Test Ignora**: trovane uno spam → click "Ignora mittente" → verifica retroactive apply (i msg di quel sender scompaiono da Inbox Triage)

**Query di verifica:**

```bash
# Decisioni create durante test
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood_stage -c "
SELECT decision, COUNT(*) 
FROM casafolino_mail_sender_decision 
WHERE active=true 
GROUP BY decision 
ORDER BY COUNT(*) DESC;
"

# Cron 96 attivo
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood_stage -c "
SELECT id, cron_name, active FROM ir_cron WHERE id=96;
"

# Policy casafolino.com
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood_stage -c "
SELECT * FROM casafolino_mail_sender_policy 
WHERE pattern_value ILIKE '%casafolino.com%';
"
```

---

## 9. Git workflow

Branch corrente: `fix/mail-v3-f6-5` (HEAD 4aca931)

**Nuovi commits da aggiungere (oltre a quelli già fatti):**

```
docs(mail-v3): F6.5 sender policy diagnostic report
fix(mail-v3): _open_next_orphan esclude current partner
feat(mail-v3): bottone "Tieni contatto" in wizard triage
feat(mail-v3): F6 auto-link leads esclude partner ignored/discarded
feat(mail-v3): UX notification chiude wizard quando queue vuota
docs(mail-v3): F6.5 report completo
```

**Push finale:** `git push origin fix/mail-v3-f6-5`

---

## 10. Ordine esecuzione

1. Verifica stato: `git status` → devi essere su `fix/mail-v3-f6-5`
2. Commit diagnostica untracked: `git add casafolino_mail/docs/diagnostica_f6_5_triage.md && git commit -m "docs..."`
3. **§3.1** Fix `_open_next_orphan` con exclude_partner_ids + update tutti i callers (5 min) → commit
4. **§3.2** Bottone "Tieni" (model method + view XML + decision type) (10 min) → commit
5. **§3.3** Filtro F6 Auto-link `_get_excluded_partner_ids` (10 min) → commit
6. **§3.4** UX notification close wizard (3 min) → commit
7. **§3.5** report_f6_5.md (5 min) → commit
8. **Push finale** `git push origin fix/mail-v3-f6-5`

**Totale: ~30-45 min autonomi.**

---

## 11. Una cosa sola

> F6.5 chiude 4 buchi in un colpo: retroactive policy (già fatto in 4aca931), Skip UX, bottone Tieni, filtro Auto-link.
>
> Senza il filtro Auto-link, F6 ti crea `crm.lead` su Giorgia Negro e simili. Col filtro, il CRM resta pulito.
>
> Commit atomici. MAI fermarti. Vai.
