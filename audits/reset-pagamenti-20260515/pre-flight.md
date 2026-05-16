# Pre-Flight Report — Reset Pagamenti CasaFolino

**Data**: 2026-05-15 18:07 UTC
**Database**: folinofood (produzione)
**Tipo**: DRY-RUN — nessuna modifica effettuata

---

## Volumi

| Metrica | Conteggio | Note |
|---------|-----------|------|
| account.payment posted | **0** | Nessuno! Tutti già non-posted |
| account.payment in_process | **20** | Da resettare a draft |
| account.bank.statement.line posted | **6.100** | Da resettare a draft |
| account_partial_reconcile | **59** | Da eliminare |
| account_full_reconcile | **1.751** | Da eliminare |
| Fatture con payment_state='paid' | **13** | Da resettare a not_paid |
| Fatture con payment_state='partial' | **1** | Da resettare a not_paid |
| Fatture con payment_state='not_paid' | **3.085** | Già OK |

### Delta vs stime del brief

| Metrica | Stima brief | Reale | Delta |
|---------|-------------|-------|-------|
| Payment posted | 1.500–2.500 | **0** | I payment non sono posted |
| Payment in_process | non previsti | **20** | Nuovo scope |
| BSL posted | ~200 residui | **6.100** | 30x più del previsto |
| Partial reconcile | migliaia | **59** | Molto meno |

---

## Saldi attuali conti 182*

| Codice | Nome | Righe | Saldo |
|--------|------|-------|-------|
| 182001 | Banca | 3.422 | −229,98 € |
| 182002 | Conto provvisorio banca (Qonto) | 2.432 | 225.422,30 € |
| 182003 | Ricevute in sospeso | 22 | 1.926,07 € |
| 182004 | Pagamenti in sospeso | 2 | 167,88 € |
| 182005 | LT353250007734964418 (Revolut) | 2.535 | 331.014,88 € |
| 182007 | BCC CASAFOLINO | 296 | 10.339,43 € |
| 182010 | Conto transito Stripe | 145 | −16.156,16 € |
| 182012 | Conto transito Amazon | 34 | −2.689,56 € |
| 182014 | Conto transito PayPal | 251 | 16.035,72 € |
| 182015 | Conto transito Dojo | 35 | −6.662,22 € |
| 182016 | Conto transito Ankorstore | 26 | −4.239,63 € |
| 182099 | Giroconti in corso | 240 | −218.329,85 € |
| **TOTALE** | | **9.440** | **336.598,88 €** |

---

## Cron da disabilitare

| ID | Nome | Stato attuale |
|----|------|---------------|
| 20 | Try to reconcile automatically your statement lines | **già inattivo** |
| 82 | CasaFolino Mail Sync V2 - Action | **attivo** → disabilitare |
| 83 | CasaFolino Silent Partners - Action | **attivo** → disabilitare |
| 84 | CasaFolino AI Classify - Action | **attivo** → disabilitare |

---

## Backup

- **File**: `/home/ubuntu/backups/pre-reset-pagamenti-20260515-1806.dump`
- **Dimensione**: 85 MB ✓ (soglia ≥50 MB superata)
- **Formato**: pg_dump custom (-Fc)

---

## Piano operativo aggiornato

Dato che la situazione reale è diversa dalle stime:

### Step 1: Disable cron 82, 83, 84
### Step 2: Delete account_partial_reconcile (59 record)
→ Automaticamente resetta `reconciled=false` e `full_reconcile_id=NULL` sulle AML coinvolte
### Step 3: Delete account_full_reconcile (1.751 record)
→ Resetta `full_reconcile_id=NULL` su tutte le AML associate
### Step 4: Reset 20 payment in_process → draft
### Step 5: Reset 6.100 BSL posted → draft (batch da 100)
### Step 6: Update payment_state='not_paid' sulle 14 fatture coinvolte
### Step 7: Recompute amount_residual su AML toccate
### Step 8: Riabilita cron
### Step 9: Genera report + CSV

### Stima durata
- Step 1-4: ~2 minuti
- Step 5 (BSL): 6.100 / 100 = 61 batch × ~3 sec = ~3 minuti
- Step 6-9: ~2 minuti
- **Totale stimato: ~7-10 minuti**

---

## ⚠️ Nota importante sui saldi 182*

I saldi dei conti provvisori (182*) sono **enormi** (336k € totale). Dopo il reset:
- I BSL torneranno draft → le loro AML sui conti 182* torneranno `parent_state='draft'`
- Le AML draft NON contano nei saldi contabili posted
- Quindi i saldi 182* **scenderanno drasticamente** dopo il reset BSL
- Il saldo finale dipende da quante AML sui 182* sono legate a BSL vs altre scritture

---

**STOP — Attendo conferma Antonio per procedere con l'esecuzione.**
