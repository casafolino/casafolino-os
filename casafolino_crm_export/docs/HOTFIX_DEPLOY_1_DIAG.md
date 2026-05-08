# Hotfix #DEPLOY.1 — Diagnosi `casafolino_card_scanner`

**Data:** 2026-05-08
**Errore:** `KeyNotFoundError: Cannot find key "casafolino_card_scanner" in the "actions" registry`

## Diagnosi

| Check | Risultato |
|---|---|
| Azione client | id=1677, name="Card Scanner SIAL", tag=`casafolino_card_scanner` |
| Menuitem | id=1020, name="Nuovo lead da biglietto", action=ir.actions.client,1677, active=true |
| Modulo proprietario | `casafolino_crm_export` (state=installed, version=18.0.9.0.0) |
| File JS | `/mnt/extra-addons/custom/casafolino_crm_export/static/src/components/card_scanner_widget.js` |
| Registrazione `registry.category("actions").add(...)` | Presente (linea 161) |
| Assets in manifest | `web.assets_backend` include js, xml, scss |
| Asset bundles in DB (`ir_attachment`) | Solo 5 bundle compilati (anomalo — dovrebbero essere decine) |
| Errori compilazione log | Nessuno |
| Ultimo update modulo | 2026-05-08 06:54:30 |
| Ultimo restart container | 2026-05-08 06:58:52 |

## Causa root identificata: Stale Asset Cache (variante Caso 3)

Codice, manifest e DB tutti corretti. Il bundle `web.assets_backend` non e' stato rigenerato dopo l'ultimo deploy. Solo 5 attachment di tipo asset presenti in DB — il bundle che include `card_scanner_widget.js` non esiste o e' stale. Il browser carica un bundle vecchio che non contiene la registrazione del componente.

## Fix proposto in Phase 1

1. Pulizia aggressiva asset cache (`DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%'`)
2. Re-update modulo `casafolino_crm_export` con `--stop-after-init --no-http`
3. Restart container
4. Verifica bundle rigenerato e azione funzionante
