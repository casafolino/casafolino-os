# Brief F7 — Hotfix Mail V3 + Triage UX Completo

**Formato:** GSD — **MODALITÀ AUTONOMA TOTALE**
**Owner:** Antonio Folino
**Base:** `fix/mail-v3-f6-5` (18.0.8.5.1, deployata in prod 20/04/2026)
**Target:** `casafolino_mail` 18.0.8.5.1 → 18.0.8.6.0
**Branch:** `fix/mail-v3-f7` (da `fix/mail-v3-f6-5`)
**Tempo stimato:** 5-7 ore autonome
**Tipo:** Hotfix bloccanti + UX triage + ingestion fix
**Prev:** F2, F2.1, F3, F4, F5, F6, F6.5

---

## 🚀 COME LANCIARE

**Sul Mac (terminale nuovo):**

```bash
cd ~/casafolino-os
git fetch --all
git checkout fix/mail-v3-f6-5
git pull
claude --dangerously-skip-permissions
```

Poi dentro Code incolla tutto il brief e scrivi "Vai".

---

## ⚠️ 4 REGOLE CRITICHE

1. **MAI fermarsi** — eccezioni: data loss prod, credenziali mancanti, architettura ambigua
2. **Defaults automatici**: naming `mv3_`, IT pro, emoji FA5, pattern esistenti, skip+annota bug pre-esistenti
3. **Auto-escape 60 min** → commit `wip`, skip, avanti (priorità: A e B vanno fatte)
4. **Commit ogni task + push ogni 3-4 commit**

---

## ORDINE PRIORITÀ SCOPO

**PRIORITY 1 — Bug bloccanti (fai PRIMA, 2h)**
- Sezione A (5 bug UI Mail V3)
- Sezione B (ingestion backlog)

**PRIORITY 2 — Polish + UX (fai DOPO, 3-4h)**
- Sezione C (Groq rate limit mitigation)
- Sezione D (triage UX)

Se auto-escape scatta a 4h, Sezione D può essere parziale — ma A, B, C devono essere chiusi.

---

## 1. Obiettivo

**Ripristinare operatività completa Mail V3 per il team CasaFolino dopo deploy F6+F6.5.** Dopo il deploy del 20/04 sono emersi bug di rendering (sidebar 360, bottoni rispondi/scrivi), backlog IMAP (email mancanti), rate limit AI, e gap UX nel triage orfani.

**Definition of Done:**

Antonio apre Mail V3 alle 9:00 domani. Sidebar 360 carica entro 2 secondi. Click "Rispondi" apre composer. Click "Scrivi" apre composer. Vede email di Gabriele Bianchi delle 11:05 di ieri (backlog recuperato). Risposta AI funziona (rate limit mitigato). Apre Triage Orfani e può selezionare 20 mittenti `noreply@` in un click e ignorarli tutti insieme.

---

## 2. Contesto dai bug

**Evidenza raccolta in chat con Antonio:**

- **Sidebar 360**: bloccata su "Caricamento" nel reading pane. No errori visibili nell'UI.
- **Bottoni "Rispondi/Tutti/Inoltra/Scrivi"**: click non apre composer. Presunto JS error che blocca tutta la UI.
- **Risposta AI**: errore `429 Client Error: Too Many Requests for url: https://api.groq.com/openai/v1/chat/completions`
- **Email Gabriele Bianchi**: in Gmail alle 11:05 del 20/04, non ingerita in Mail V3 pur essendo cron 82 attivo (lastcall 14:03:53, nextcall 14:16:33). Ultime email create_date 14:24 contengono email_date di 27-38h fa. Backlog accumulato.
- **Triage**: query DB mostra 28 orfani in `casafolino_mail_orphan_partner`. `Skip` funzionante dopo F6.5 ma mancano bulk actions. Molti orfani sono `noreply@*` che vorremmo auto-processare.

---

## 3. Scope IN — 9 deliverable

### PRIORITY 1 — PRIMA

### 3.1 Fix JS error bloccante sidebar 360 + bottoni (1h)

**Prima diagnosi necessaria** — NON partire col fix alla cieca. Esegui in ordine:

1. `docker logs odoo-app --since 1h 2>&1 | grep -iE "ERROR|traceback|mail_v3|sidebar" | tail -50`
2. Apri reading pane di un thread e cattura errori console browser (via selenium/curl — o chiedi feedback ad Antonio)
3. Verifica endpoint `/cf/mail/v3/partner/<id>/commercial_context` risponde senza errore
4. Verifica endpoint `/cf/mail/v3/thread/<id>/reply_context` (o simile per comporre reply) risponde

**Ipotesi principale**: un componente OWL (probabilmente `SidebarCommercialContext`) lancia eccezione in `onWillStart` che propaga a tutto il client e blocca altre componenti (composer, action buttons).

**Fix pattern:**

1. Identifica il componente che crasha dai log
2. Wrap `onWillStart` + `onMounted` con try/catch che logga e prosegue con fallback state
3. Esempio:
```javascript
onWillStart(async () => {
    try {
        const result = await this.orm.call('casafolino.mail.thread', 'get_commercial_context', [this.props.partnerId]);
        this.state.context = result;
    } catch (e) {
        console.error('[mail v3] commercial context fetch failed:', e);
        this.state.context = null;
        this.state.error = true;
    }
});
```
4. Template XML: `<t t-if="!state.error" ...>` per non rompere render se API fallisce

**Se la diagnosi rivela un errore backend specifico** (es. `cf_mail_thread_id` field missing, SQL error), fixa quello invece + aggiungi il try/catch come safety net.

### 3.2 Fix compose wizard non apre da "Rispondi / Tutti / Inoltra / Scrivi" (0.5h)

Stesso sintomo: click su bottoni non apre modal. Possibili cause:

- `doAction` silenziosamente fallisce perché il wizard transient richiede context che non viene passato
- F6 ha aggiunto `template_id` campo required che non ha default, wizard create fallisce
- Sidebar 360 crash blocca event handler su bottoni (dipendenza inversa)

**Verifica:**
1. Se 3.1 risolve anche i bottoni (dipendenza inversa) → già fatto
2. Altrimenti: apri `casafolino_mail/static/src/js/mail_v3/mail_v3_reading_pane.js` (o file del reading pane), cerca il metodo che gestisce click "Rispondi"
3. Controlla che il `doAction` passi context pulito: `{ default_thread_id, default_partner_id, default_reply_mode: 'reply' }`
4. Se il wizard ha required fields nuovi da F6 (es. `template_id`, `scheduled_send_at`), controlla che non siano required senza default

### 3.3 Fix ingestion IMAP backlog (0.5h)

**Diagnosi**:
```sql
SELECT COUNT(*) FILTER (WHERE body_downloaded=false) AS pending_body,
       COUNT(*) FILTER (WHERE body_downloaded=true) AS done_body,
       COUNT(*) AS total
FROM casafolino_mail_message WHERE account_id=1;

SELECT COUNT(*) FROM casafolino_mail_message_staging;
```

**3 possibili fix in base alla diagnosi:**

**Fix A**: se `pending_body > 500` → cron 85 body fetch è collo di bottiglia. Aumenta batch size (cerca `body_fetch_batch` o simile, default 10) a 50 + diminuisci interval da 5m → 2m (o in `ir_cron` SQL: UPDATE interval_number).

**Fix B**: se `staging > 100` → staging processing è lento. Cerca metodo che promuove staging → message, aumenta batch da default a 200.

**Fix C**: se `pending_body < 50` e staging vuoto ma l'email Gabriele comunque non c'è → è un edge case IMAP (email in cartella All Mail/Archivio che il cron non sincronizza). Estendi la lista `folders_to_fetch` in `casafolino_mail_account.py` per includere INBOX + Sent + "[Gmail]/All Mail" o label specifiche.

**In più** — Hotfix one-shot: forza ingestion ultime 48h per account 1:
```python
# Via odoo shell o endpoint admin
account = env['casafolino.mail.account'].browse(1)
account.last_fetch_datetime = fields.Datetime.now() - timedelta(days=2)
account.action_fetch_now()  # forza un ciclo manuale
```

Documenta nel report quale fix hai applicato.

### 3.4 Commit + push batch PRIORITY 1 (stop per verifica)

Dopo 3.1, 3.2, 3.3 **commit + push**. Antonio potrà deployare stage e verificare. Dopo conferma, continuare con PRIORITY 2.

### PRIORITY 2 — DOPO

### 3.5 Groq rate limit mitigation (0.5h)

Errore `429 Too Many Requests` da Groq. Fix non è "rimuovere errore", è gestirlo meglio.

**Implementazione:**

1. File: `casafolino_mail/models/` (cerca chi chiama `api.groq.com`)
2. Wrapper con **retry + exponential backoff**:
```python
import time
import requests

def _call_groq_with_retry(self, payload, max_retries=3):
    base_delay = 2  # seconds
    for attempt in range(max_retries):
        try:
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                json=payload,
                headers={'Authorization': f'Bearer {self._get_groq_key()}'},
                timeout=30,
            )
            if response.status_code == 429:
                # Rate limited — wait and retry
                retry_after = int(response.headers.get('retry-after', base_delay * (2 ** attempt)))
                _logger.warning('[groq] 429, retry in %ss (attempt %s/%s)', retry_after, attempt+1, max_retries)
                time.sleep(min(retry_after, 10))  # cap at 10s
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise UserError(f'Risposta AI non disponibile al momento. Riprova tra qualche secondo. ({str(e)[:100]})')
            time.sleep(base_delay * (2 ** attempt))
    raise UserError('Risposta AI non disponibile dopo 3 tentativi.')
```

3. UI: se fallisce dopo 3 tentativi, mostra messaggio "Risposta AI non disponibile, riprova tra qualche secondo" invece di stacktrace

4. **Aggiungi throttling globale**: non più di 1 chiamata Groq ogni 2 secondi per utente (contatore in cache Odoo o in `res.users`)

### 3.6 Triage Orfani — Bulk Actions (1h)

**Nuovo wizard bulk** `casafolino.mail.orphan.bulk.wizard` (TransientModel):

```python
class OrphanBulkWizard(models.TransientModel):
    _name = 'casafolino.mail.orphan.bulk.wizard'
    
    orphan_ids = fields.Many2many('casafolino.mail.orphan.partner', string='Orfani selezionati')
    action_type = fields.Selection([
        ('ignore_sender', 'Ignora tutti (auto_discard)'),
        ('ignore_domain', 'Ignora tutti i domini'),
        ('keep', 'Tieni tutti come validi'),
        ('snippet', 'Rispondi con snippet'),
    ], required=True)
    snippet_id = fields.Many2one('casafolino.mail.snippet')  # se action_type=snippet
    
    def action_apply_bulk(self):
        # Per ciascun orphan, crea decisione + policy (se ignore)
        # Retroactive apply policy (già presente in F6.5)
        # Log count operazioni
        ...
```

**Menu**: "Triage Orfani" ora ha 2 entry:
- "Wizard singolo" (esistente)
- "Gestione massiva" → apre list view di `casafolino.mail.orphan.partner` con multi-select + action in header

**List view**:
```xml
<list multi_edit="1">
    <header>
        <button name="action_bulk_ignore_sender" string="Ignora selezionati" type="object" class="btn btn-danger"/>
        <button name="action_bulk_keep" string="Tieni selezionati" type="object" class="btn btn-success"/>
    </header>
    <field name="partner_name"/>
    <field name="partner_email"/>
    <field name="sender_domain"/>
    <field name="inbound_count_90d"/>
    <field name="priority"/>
</list>
```

**Search view** con filtri pre-configurati:
- "Solo noreply@"
- "Solo newsletter (bounce/info/noreply/no-reply/automated)"
- "Priority cold"
- "Ultimi 7 giorni"

### 3.7 Auto-pulizia noreply@ (0.5h)

Cron una-tantum o azione amministratore che:

1. Identifica orfani con sender_email matching regex: `^(noreply|no-reply|donotreply|mailer-daemon|postmaster|info|news|newsletter|automated|notification)@.*$`
2. Crea decisione `auto_discarded_system` per tutti
3. Crea policy `auto_discard` per ciascun dominio (dedup)
4. Retroactive apply su tutti i messaggi esistenti di quei mittenti

**Endpoint admin**: `/cf/mail/v3/triage/autoclean_noreply` (POST, admin only) → ritorna `{"cleaned": N, "domains_added": M}`

**Menu**: "Impostazioni → Triage → Pulizia automatica noreply@"

### 3.8 Migliora info wizard Orfano (0.5h)

Aggiungi al wizard `casafolino.mail.triage.wizard` questi campi computed (read-only, visualizzati in form):

- `sender_tld` (es. `.de`, `.it`, `.com`)
- `sender_language_hint` (Char) — estratto da ultimo email body
- `is_likely_buyer` (Boolean) — True se subject contiene keyword commerciali: quote, offer, sample, interesse, prezzo, listino, buyer, importer, distributor
- `partner_website_detected` (Char) — se email dominio sembra azienda (non gmail/libero/yahoo), mostra dominio
- `similar_partners_count` (Integer) — count partner esistenti con stesso dominio

Mostrali in sezione "Indizi" prima dei bottoni decisione.

**Opzionale bonus**: bottone "🔍 Cerca su Google" che apre nuova tab con query `site:{domain} OR {partner_name} food importer`. Aiuta decisione rapida.

### 3.9 Report f7.md (0.3h)

Template standard + sezioni:

- Bug fix applicati (A: sidebar, bottoni; B: ingestion)
- Soluzione Groq 429
- Feature triage bulk + auto-noreply + info enrichment
- Query SQL one-shot eseguite (fetch backlog, policy seed)
- AC coverage
- Raccomandazioni F8 (WhatsApp, Calendar, Multi-lingua, Hotness auto-calibrata)

---

## 4. Scope OUT

- ❌ NO modifiche architetturali (no nuovi modelli core)
- ❌ NO toccare cron 94/95/96 F6/F6.5 (appena deployati, lasciali in osservazione)
- ❌ NO toccare UI Mail V3 composer wizard (già unificato in F5)
- ❌ NO toccare record rules F2.1
- ❌ NO refactor intelligence engine
- ❌ NO WhatsApp/Calendar/Multi-lingua (F8+)

---

## 5. Vincoli Odoo 18

Standard (come sempre):
1. No `attrs=`, sì `invisible=domain`
2. No `<tree>`, sì `<list>`
3. No `_inherit` in `ir.model.access.csv`
4. OWL `static props = ["*"]`
5. Try/catch in onWillStart/onMounted (pattern Odoo 18 OWL safety)
6. `ensure_one()` in metodi action
7. `sudo()` cross-user

---

## 6. Acceptance Criteria (14 AC)

### Bug fix (bloccanti)
- **AC1** Sidebar 360 carica in <3 sec quando click su thread (non più "Caricamento" infinito)
- **AC2** Click "Rispondi" apre compose wizard modal con thread context
- **AC3** Click "Tutti" (reply all) apre wizard con to+cc prefilled
- **AC4** Click "Inoltra" apre wizard con body originale prefilled
- **AC5** Click "Scrivi" (header Mail V3) apre wizard vuoto
- **AC6** Email Gabriele Bianchi delle 11:05 20/04 presente in DB entro 1h dal deploy (forced resync)
- **AC7** delay_minutes medio ultime 100 email < 30 min (no più backlog multi-ora)

### Groq
- **AC8** 429 Groq non più visibile all'utente — mostra "Riprova" user-friendly
- **AC9** Retry automatico 3 tentativi con backoff
- **AC10** Throttling max 1 call Groq / 2 sec per utente

### Triage UX
- **AC11** Bulk wizard disponibile: selezione 20+ orfani → "Ignora" in 1 click
- **AC12** Auto-pulizia noreply@ rimuove >=80% degli orfani di tipo notifica
- **AC13** Info enrichment wizard mostra TLD, is_likely_buyer, similar_partners count
- **AC14** Search view orfani ha filtro "Solo noreply@" predefinito

---

## 7. Deploy path

**Sul Mac**:
```bash
cd ~/casafolino-os && \
git push origin fix/mail-v3-f7
```

**Sul server EC2 (ssh ubuntu@51.44.170.55)**:

**STAGE FIRST — test 10 min UI prima di prod**:
```bash
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo -Fc folinofood_stage > /tmp/stage_pre_f7_$(date +%Y%m%d_%H%M%S).dump && \
cd /home/ubuntu/casafolino-os && \
git fetch --all && \
git checkout fix/mail-v3-f7 && \
git pull && \
sudo cp -rf casafolino_mail /docker/enterprise18/addons/custom/ && \
docker exec odoo-app odoo -d folinofood_stage -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f7_stage.log | tail -80 && \
grep -E "ERROR|CRITICAL|Traceback" /tmp/f7_stage.log
```

**Test UI stage** (5 min):
1. Login `https://erp.casafolino.com/web?db=folinofood_stage`
2. Mail V3 → click thread → sidebar 360 carica? ✓
3. Click "Rispondi" → wizard apre? ✓
4. Test "Scrivi" → wizard apre? ✓
5. Test AI reply → no 429 visibile? ✓

**PROD SOLO SE STAGE OK**:
```bash
docker exec -e PGPASSWORD=odoo odoo-db pg_dump -U odoo -Fc folinofood > /tmp/prod_pre_f7_$(date +%Y%m%d_%H%M%S).dump && \
docker exec odoo-app odoo -d folinofood -u casafolino_mail --stop-after-init --no-http 2>&1 | tee /tmp/f7_prod.log | tail -80 && \
grep -E "ERROR|CRITICAL|Traceback" /tmp/f7_prod.log && \
docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "DELETE FROM ir_attachment WHERE name LIKE '%web.assets%';" && \
docker restart odoo-app
```

**Sleep 30s + verify**:
```bash
sleep 30 && docker exec -e PGPASSWORD=odoo odoo-app psql -h odoo-db -U odoo folinofood -c "
SELECT name, latest_version, state FROM ir_module_module WHERE name='casafolino_mail';
"
```

Atteso: `18.0.8.6.0 installed`.

**Force ingestion backlog account 1 (hotfix one-shot)**:
```bash
docker exec -e PGPASSWORD=odoo odoo-app odoo shell -d folinofood --no-http 2>&1 <<'EOF'
from datetime import timedelta
account = env['casafolino.mail.account'].browse(1)
account.last_fetch_datetime = fields.Datetime.now() - timedelta(days=2)
account.action_fetch_now()
env.cr.commit()
print(f"Forced fetch for account {account.email_address}")
EOF
```

---

## 8. Git workflow

Branch: `fix/mail-v3-f7` da `fix/mail-v3-f6-5`.

Commits atomici in ordine:
```
fix(mail-v3): try/catch safety onWillStart sidebar 360 (fix blocking UI)
fix(mail-v3): compose wizard button handlers (reply/all/forward/new)
fix(mail-v3): IMAP backlog hotfix + batch size body fetch
--- BATCH 1 PUSH ---
feat(mail-v3): Groq 429 retry + backoff + throttling
feat(mail-v3): triage orphan bulk wizard + list view actions
feat(mail-v3): auto-cleanup noreply@ mittenti
feat(mail-v3): orphan wizard info enrichment (TLD, buyer hints)
--- BATCH 2 PUSH ---
chore(mail-v3): manifest bump 18.0.8.6.0
docs(mail-v3): F7 report
```

Push dopo batch 1 (priority 1 chiusa) e push finale.

---

## 9. Ordine esecuzione

1. `git checkout -b fix/mail-v3-f7 fix/mail-v3-f6-5`
2. Leggi brief + report_f6_5.md
3. **§3.1 DIAGNOSI** log + console errors → identifica bug sidebar 360
4. **§3.1 FIX** try/catch OWL + fix backend endpoint se necessario → commit
5. **§3.2** Fix compose wizard buttons → commit
6. **§3.3 DIAGNOSI** query body_fetch + staging → identifica Fix A/B/C
7. **§3.3 FIX** applica fix diagnosticato + hotfix one-shot backlog → commit
8. **PUSH BATCH 1** → stop per verifica Antonio
9. **§3.5** Groq retry + backoff → commit
10. **§3.6** Triage bulk wizard + list view → commit
11. **§3.7** Auto-cleanup noreply@ → commit
12. **§3.8** Wizard info enrichment → commit
13. Manifest bump 18.0.8.6.0
14. **§3.9** report_f7.md
15. **PUSH FINALE**

**Totale: ~5-7h autonome.**

---

## 10. Una cosa sola

> F7 è il ripristino operativo. Senza questo, domattina Josefina/Martina/Maria aprono Mail V3 e non possono lavorare.
>
> PRIORITY 1 (sidebar + bottoni + ingestion) è vita o morte.
> PRIORITY 2 (Groq + triage UX) è dignità del prodotto.
>
> MAI fermarti. 4 regole. Vai.
