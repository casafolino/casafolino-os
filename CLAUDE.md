# CasaFolino OS — Istruzioni per Claude Code

## Progetto
Modulo Odoo 18 custom per CasaFolino Srls (azienda food italiana).
Repository: casafolino-os

## Regole critiche Odoo 18 OWL — NON violare mai
1. Mai arrow function con blocco `{}` nei `t-on-change` — usa sempre un metodo dedicato
2. Mai `@import url()` esterni nel CSS
3. Mai `useService('rpc')` — usa `import { rpc } from "@web/core/network/rpc"`
4. Mai `attrs=` nelle view XML — usa `invisible=`, `readonly=`
5. Mai parentesi tonde `()` negli `invisible` — usa `[]`
6. Mai `web.assets_web` — usa `web.assets_backend`
7. Mai arrow function con blocco `{}` nei `t-on-change` — crea sempre un metodo nel componente

## Brand
- Colore accent: #5A6E3A (verde CasaFolino)
- Font: sistema sans-serif

## Deploy
Il deploy avviene tramite ~/deploy.sh sul server

## Moduli custom
casafolino_mail, casafolino_allergen, casafolino_nutrition, casafolino_kpi,
casafolino_treasury, casafolino_gdo, casafolino_private_label, casafolino_crm_export,
casafolino_production, casafolino_recall, casafolino_supplier_qual, casafolino_haccp
