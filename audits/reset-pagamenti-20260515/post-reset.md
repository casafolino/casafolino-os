# Post-Reset Report — Reset Pagamenti CasaFolino

**Data**: 2026-05-15
**Database**: folinofood (produzione)
**Operazione**: Reset completo pagamenti e riconciliazioni

---

## Risultato: SUCCESSO

Tutti i criteri di accettazione soddisfatti.

---

## Delta Pre/Post

| Metrica | Pre-reset | Post-reset | Azione |
|---------|-----------|------------|--------|
| account.payment posted | 0 | 0 | n/a |
| account.payment in_process | 20 | 0 | → draft |
| account.payment draft | 0 | 20 | ✓ |
| BSL posted | 6.100 | 0 | → draft |
| BSL draft | 0 | 6.100 | ✓ |
| account_partial_reconcile | 59 | 0 | eliminati |
| account_full_reconcile | 1.751 | 0 | eliminati |
| AML reconciled=true | 2.658 | 0 | → false |
| AML amount_residual corretti | — | 24.100 | ricalcolati |
| Fatture paid | 13 | 0 | → not_paid |
| Fatture partial | 1 | 0 | → not_paid |
| Fatture not_paid | 3.085 | 3.099 | +14 |

---

## Saldi conti 182* Post-Reset

| Codice | Nome | Pre-reset | Post-reset |
|--------|------|-----------|------------|
| 182001 | Banca | −229,98 € | **0 €** (righe ora draft) |
| 182002 | Conto provvisorio banca | 225.422,30 € | **441.579,43 €** (31 righe POS residue) |
| 182003 | Ricevute in sospeso | 1.926,07 € | **0 €** |
| 182004 | Pagamenti in sospeso | 167,88 € | **0 €** |
| 182005 | Revolut provvisorio | 331.014,88 € | **0 €** |
| 182007 | BCC CASAFOLINO | 10.339,43 € | **0 €** |
| 182010 | Conto transito Stripe | −16.156,16 € | **0 €** |
| 182012 | Conto transito Amazon | −2.689,56 € | **0 €** |
| 182014 | Conto transito PayPal | 16.035,72 € | **0 €** |
| 182015 | Conto transito Dojo | −6.662,22 € | **0 €** |
| 182016 | Conto transito Ankorstore | −4.239,63 € | **0 €** |
| 182099 | Giroconti in corso | −218.329,85 € | **0 €** |

### Nota su 182002

Le 31 righe residue (441.579 €) sono tutte **journal entry POS** ("Punto vendita" — POSS/2024/*, POSS/2025/*, POSS/2026/*). Sono write-off e transfer tra 150100↔250100↔182002 generate dal modulo POS. **Non sono legate a pagamenti bancari** e non rientrano nello scope di questo reset.

---

## Verification Battery

| Check | Risultato |
|-------|-----------|
| V1: Payments posted = 0 | ✓ |
| V2: Payments in_process = 0 | ✓ |
| V3: BSL posted = 0 | ✓ |
| V4: Partial reconcile = 0 | ✓ |
| V5: Full reconcile = 0 | ✓ |
| V6: Fatture non-not_paid = 0 | ✓ |
| V7: AML still reconciled = 0 | ✓ |
| V8: Cron 82 attivo | ✓ |
| V9: Cron 83 attivo | ✓ |
| V10: Cron 84 attivo | ✓ |
| V11: BSL draft = 6.100 | ✓ |
| V12: Payments draft = 20 | ✓ |

---

## Backup

- **File**: `/home/ubuntu/backups/pre-reset-pagamenti-20260515-1806.dump`
- **Dimensione**: 85 MB
- **Formato**: pg_dump custom (-Fc)
- **Restore**: `pg_restore -h odoo-db -U odoo -d folinofood_restore /home/ubuntu/backups/pre-reset-pagamenti-20260515-1806.dump`

---

## File generati

| File | Righe | Descrizione |
|------|-------|-------------|
| `02-clienti-aperti.csv` | 783 | Fatture/NC clienti non pagate |
| `03-fornitori-aperti.csv` | 2.316 | Fatture/NC fornitori non pagate |
| `04-bsl-da-matchare.csv` | 6.106 | BSL bancari in draft pronti per riconciliazione |
| `pre-flight.md` | — | Report pre-esecuzione |
| `post-reset.md` | — | Questo report |

---

## Operazioni eseguite (in ordine)

1. **Backup** pg_dump -Fc → 85 MB ✓
2. **Disable cron** 82, 83, 84 → `active=false`
3. **Delete** 59 `account_partial_reconcile`
4. **Delete** 1.751 `account_full_reconcile`
5. **Reset AML** `reconciled=false`, `full_reconcile_id=NULL` su 2.658 righe
6. **Recompute** `amount_residual = balance` su 24.100 AML
7. **Reset payments** 20 `in_process` → `draft` (move + AML + payment)
8. **Reset BSL** 6.100 `posted` → `draft` (move + 12.573 AML)
9. **Reset fatture** 14 `payment_state` → `not_paid`
10. **Re-enable cron** 82, 83, 84 → `active=true`

---

## Prossimi passi

1. **Restart Odoo** per pulire cache ORM:
   ```bash
   docker restart odoo-app
   ```

2. **Verificare widget riconciliazione**: Contabilità → Rendicontazione bancaria → tutti e 3 i journal (Qonto, Revolut, BCC) devono mostrare i BSL pronti per matching.

3. **Riconciliare BSL ↔ fatture**: iniziare dal widget, matching manuale o automatico.

4. **Indagare 182002 POS**: le 31 righe POS residue (441k €) vanno analizzate separatamente — probabilmente serve un reset anche delle sessioni POS o una pulizia delle entry manuali Punto vendita.

5. **Nessuna scrittura cancellata**: tutte le fatture, BSL e payment esistono ancora. Solo lo stato è cambiato.

---

*Report generato il 2026-05-15. Nessuna query di scrittura distruttiva (DELETE su move/AML) eseguita — solo reset stato e pulizia riconciliazioni.*
