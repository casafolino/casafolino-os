# CasaFolino Shopify Sync

Modulo Odoo 18 per sincronizzare:

- quantita disponibili da Odoo a Shopify
- ordini da Shopify a Odoo
- mapping prodotti tramite SKU (`product.product.default_code`)

## Shopify

Creare una custom app Shopify con questi scope Admin API:

- `read_products`
- `read_inventory`
- `write_inventory`
- `read_orders`

Versione GraphQL usata di default: `2026-04`.

Webhook da configurare:

- topic: `orders/create`
- URL: `https://<odoo-domain>/shopify/webhook/orders/create`
- secret: lo stesso valore configurato in Odoo

## Odoo

Configurare da Impostazioni -> Shopify Sync:

- dominio Shopify, esempio `nome-store.myshopify.com`
- Admin API access token
- Shopify Location GID, esempio `gid://shopify/Location/123456789`
- magazzino Odoo da cui leggere `free_qty`
- webhook secret Shopify

Il cron `CasaFolino Shopify: sync stock` viene creato disattivato. Attivarlo dopo avere configurato token e location.

## Regole dati

- Lo SKU Shopify deve coincidere con `Riferimento interno` Odoo.
- Se un ordine Shopify contiene uno SKU non trovato, l'ordine non viene creato e viene scritto un log errore.
- Se il prodotto Odoo non ha SKU, lo stock non viene inviato a Shopify.
- Odoo invia a Shopify la quantita disponibile (`free_qty`) del magazzino configurato.

