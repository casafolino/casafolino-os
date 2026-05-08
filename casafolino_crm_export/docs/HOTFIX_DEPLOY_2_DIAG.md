# Hotfix #DEPLOY.2 — Diagnosi profonda `casafolino_card_scanner` recidivo

**Data:** 2026-05-08
**Errore:** `KeyNotFoundError: Cannot find key "casafolino_card_scanner" in the "actions" registry`
**Hash bundle invariato:** `b5a6464` (non rigenerato dopo Hotfix #1)

## Diagnosi — 11 check eseguiti

| # | Check | Risultato |
|---|---|---|
| A | File JS sul server | `/mnt/extra-addons/custom/casafolino_crm_export/static/src/components/card_scanner_widget.js` — presente |
| B | JS registration line 161 | `registry.category("actions").add("casafolino_card_scanner", CardScannerWidget)` — corretto |
| C | Diff Mac vs Server | Identico (5103 bytes entrambi) |
| D | Manifest assets | `web.assets_backend` include js, xml, scss — corretto |
| E | Manifest paths vs filesystem | Tutti OK (9/9 file JS matchano) |
| F | Tag DB | id=1677, tag=`casafolino_card_scanner` — corretto |
| G | Bundle compilation | `web.assets_web.min.js` hash `b5a6464` (8.5MB) — compilato ma STALE |
| H | Stringa nel bundle | **ASSENTE** — 0 occorrenze di `casafolino_card_scanner` nel bundle compilato |
| I | curl bundle | HTTP 200, Last-Modified: April 18 2026 — bundle vecchio di 20 giorni |
| J | Log errori | Nessun errore compilazione JS |
| K | Module state | `casafolino_crm_export`: **`to upgrade`** (non `installed`) |

## Indagine avanzata

| Check | Risultato |
|---|---|
| Odoo 18 bundle architecture | `web.assets_web` include `web.assets_backend` via `('include', 'web.assets_backend')` |
| `ir_asset` table | 0 entries per casafolino_crm_export (normale: manifest assets letti direttamente) |
| Moduli nel bundle | casafolino_commercial, haccp, kpi, product, supplier_qual presenti. **casafolino_crm_export ASSENTE** |
| Module states | 7 moduli stuck in `to upgrade`: crm_export, mail, fair_report, initiative_dashboard, mail_stats, mail_templates, workspace |
| Odoo startup ERROR | `"Some modules have inconsistent states, some dependencies may be missing"` per tutti e 7 |
| Models in registry | `casafolino.mail.message`, `casafolino.mail.raw`, `casafolino.mail.account` — KeyError (NON nel registry) |
| Dependency analysis | **DIPENDENZA CIRCOLARE**: `casafolino_mail` depends `casafolino_crm_export` E `casafolino_crm_export` depends `casafolino_mail` |

## Causa root identificata: DIPENDENZA CIRCOLARE

```
casafolino_mail → depends → casafolino_crm_export
casafolino_crm_export → depends → casafolino_mail
```

Odoo non riesce a costruire il grafo delle dipendenze → salta il caricamento di TUTTI i 7 moduli nel cluster circolare → codice Python non caricato → assets non compilati nel bundle → `casafolino_card_scanner` mai registrato nel browser.

La dipendenza di `casafolino_mail` su `casafolino_crm_export` esiste per UNA sola ragione:
- XML view `inherit_id ref="casafolino_crm_export.cf_crm_lead_view_form_premium"` in `casafolino_mail/views/casafolino_mail_hub_views.xml` (riga 363)

## Fix in Phase 1

1. Rimuovere `casafolino_crm_export` dal `depends` di `casafolino_mail/__manifest__.py`
2. Spostare la view ereditata in `casafolino_crm_export/views/crm_lead_views.xml` (che gia' dipende da `casafolino_mail`)
3. Pulire record `ir_model_data` orfano del vecchio external ID
4. Deploy entrambi i moduli
5. Update con `-u casafolino_mail,casafolino_crm_export`
6. Verificare: moduli `installed`, stringa nel bundle, hash cambiato
