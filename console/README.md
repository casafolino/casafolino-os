# Console commerciale CasaFolino

Standalone **Next.js** (App Router, TypeScript) che legge Odoo (`folinofood`) via
**JSON-RPC**. Tema chiaro fedele a `docs/design/console_reference_v4.html`.
Principi: **relazione per partner**, **mail ovunque**, **no-trattino**.

## Avvio (mock-first)
```bash
cd console
npm install
npm run dev        # http://localhost:3000  (CONSOLE_USE_MOCK=1 di default senza credenziali)
```
In mock mode usa fixtures locali (`lib/mock.ts`, partner Klaus Berger/Neumann): nessun
Odoo richiesto, UI completamente navigabile.

> ⚠️ Non lanciare `npm run build` mentre `npm run dev` è attivo: corrompe `.next` del
> dev (CSS 404). Per il build: ferma il dev, `rm -rf .next`, poi `npm run build`.

## Schermi (6 sezioni)
| Route | Schermo |
|---|---|
| `/` | Regia — command center (KPI, "Ti aspetta", barra pipeline) |
| `/inbox` | Inbox 3-pane (contesto **dal mittente**, "Mail con questo partner") |
| `/pipeline` | Pipeline kanban (card bordo-sx colore operatore, score, badge) |
| `/dossier` | Dossier 360 (header, KPI strip, tab incl. Mail, timeline) |
| `/follow-up` | Follow-up 4 colonne |
| `/fiere` | Fiere |
| `/debug` | Diagnostica data layer |

## Architettura
- **Data layer** `lib/bundle.ts`: `getPartnerBundle(partnerId)` → `{ partner, leads,
  dossiers, orders, revenue, mailThread, signals }` con **cache** TTL. Un solo bundle,
  consumato da tutte le viste → **mail ovunque**. `resolveBySender(email)` risolve il
  partner dal mittente (exact/dominio) **senza richiedere un lead**.
- **Client Odoo** `lib/odoo.ts` (solo server): `authenticate`/`callKw`/`searchRead`/
  `getConfigParam`. Toggle mock via `shouldUseMock()`.
- **Componenti riusabili**: `PartnerContext`, `PartnerMailThread`, `RelationshipTimeline`,
  `Sidebar` (full/rail), `Icons`. `Honest` = helper **no-trattino** (mai "—": dato reale
  o vuoto-onesto-con-azione).
- **Scritture SOLO via Odoo** (`lib/writes.ts` + `/api/write`): crea lead, collega mail,
  invio email via **`mail.mail`** (mai SMTP raw).
- **Bozza AI** (`lib/ai.ts` + `/api/ai-draft`): **Groq** (`llama-3.3-70b-versatile`),
  chiave da `GROQ_API_KEY` o `casafolino.groq_api_key` (Odoo). **Non** usa `cf.gemini.client`.

## Collegamento a Odoo stage
1. `cp .env.example .env.local` e riempi (`.env.local` è gitignorato):
   `ODOO_URL`, `ODOO_DB=folinofood_stage`, `ODOO_USERNAME`, `ODOO_API_KEY`, `CONSOLE_USE_MOCK=0`.
2. I getter hanno il path Odoo: `getPartnerBundle`/`resolveBySender` sono **completi**;
   `getRegia` parziale; `getInbox`/`getPipeline`/`getDossier`/`getFollowup`/`getFiere`
   sono **stub** (ritornano vuoto) — da completare e **testare sullo stage** prima di Vercel.
3. Tutte le letture via JSON-RPC, tutte le scritture via i canali Odoo.

## Deploy Vercel (gate umano)
- Env **separati** per ambiente: Preview → stage, Production → prod (`ODOO_DB` diverso).
- **Nessun segreto nel repo**: `.env*`/`.env.local` gitignorati; chiavi solo negli env Vercel.
- Le scritture in prod passano dai canali Odoo sicuri (`mail.mail`, ORM create/write).

## Stato acceptance
1. ✅ `getPartnerBundle` → mailThread per partner, usato da tutte le viste.
2. ✅ Klaus Berger: mail in contatto+lead+pipeline-card-context+dossier (stesso bundle).
3. ✅ Inbox: contesto dal mittente anche senza lead.
4. ✅ Zero "—": empty-state onesti con azione.
5. ✅ Bozza AI via Groq (mock fallback senza chiave).
6. ✅ Scritture/invii via Odoo (`mail.mail`, mai SMTP raw).
7. ⏳ Test su stage + Vercel: env separati e zero-segreti pronti; **test reads/writes su
   stage da eseguire con credenziali** (poi deploy).
