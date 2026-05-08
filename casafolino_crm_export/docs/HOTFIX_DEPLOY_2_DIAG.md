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

## Fix applicato — Phase 1

### Operazioni
1. Rimosso `casafolino_crm_export` da `depends` in `casafolino_mail/__manifest__.py`
2. Spostata view `view_crm_lead_form_premium_mail_hub` in `casafolino_crm_export/views/crm_lead_views.xml`
3. Pulito record `ir_model_data` orfano (`DELETE 1`)
4. Rimossa dependency circolare da `ir_module_module_dependency` (`DELETE 1`)
5. Deploy entrambi i moduli + `-u casafolino_mail,casafolino_crm_export`
6. Asset cache pulita

### Verifiche
- **Module states**: tutti 16 moduli casafolino `installed`
- **Inconsistent states error**: ASSENTE (risolto)
- **KeyError su modelli casafolino**: ASSENTE (modelli caricati nel registry)
- **Dependency casafolino_mail**: `base, crm, mail, utm, web` (no piu' casafolino_crm_export)
- **Action DB**: id=1677, tag=`casafolino_card_scanner` presente
- **Container**: UP
- **HTTP**: 200
- **Bundle `web.assets_web`**: compilazione lazy, sara' rigenerato al primo login backend con NUOVO hash (non piu' b5a6464)

### Warning non-bloccante
`project.project.cf_status_dossier` domain error in `posizionatore_views.xml` — view validation warning, non impedisce funzionamento. Da correggere separatamente.
