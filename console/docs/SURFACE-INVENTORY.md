# CRM Console v2 — Inventario superfici (F0)

Mappa `file → ruolo` dei tre surface (pipeline · contatti/dossier · record lead) + fondamenta condivise.
Stack: Next.js 15 (app router) + React 19, **niente Tailwind**. Styling = `app/globals.css` (CSS vars `console_reference_v4`) + stili inline + sprite SVG (`components/Icons.tsx`). Dati da Odoo via route `/api/console/*` → gateway `casafolino_console_access` (JSON-RPC, utente `console_prod_rw`/`console_api`).

## Fondamenta / shell
| File | Ruolo |
|---|---|
| `app/layout.tsx` | Root layout; monta `IconSprite` + `globals.css` |
| `app/globals.css` | **Design tokens canonici** (palette, semantica ok/warn/danger, radius, font) + classi base (`.card`, `.chip`, `.btn*`, `.kpi`, `.empty-honest`, `.tl-*`, `.mail-*`) |
| `lib/theme.ts` | Palette operatori + mapping login→operatore (colori owner) |
| `lib/tokens.ts` | **(F0 nuovo)** mirror TS dei token CSS + scale rotting/azione — single source per i componenti |
| `components/ds/` | **(F0 nuovo)** atomi DS riusabili: `Pill`, `Avatar`, `RailCard`, `Toast`, `Money` |
| `components/Icons.tsx` | Sprite SVG (set unico: home/inbox/mail/kanban/clock/fair/folders/reply/ai/link/check/alert) — **riusare questo, non aggiungere librerie icone** |
| `components/Sidebar.tsx` | Navigazione laterale (full + variante `rail`) |
| `components/Honest.tsx` | `moneyCompact`, `dateLabel`, vuoti onesti (mai "—" nudo) |
| `lib/basePath.ts` | `BP` = basePath `/console` per fetch |
| `lib/odoo.ts` / `lib/odooAuth.ts` | Client JSON-RPC + auth verso Odoo |
| `lib/types.ts` | Tipi condivisi (OperatorKey…) |

## Surface 1 — Pipeline (kanban)
| File | Ruolo |
|---|---|
| `app/pipeline/page.tsx` | Route server; monta `KanbanBoard` |
| `components/KanbanBoard.tsx` | Board: colonne=stage non terminali, DnD ottimistico→`set-stage`, menu card→stage terminali, card→`/lead/[id]` |
| `lib/pipeline.ts` | Tipi `Board`/`BoardColumn`/`BoardCard` + client `getBoard`/`setLeadStage`/`universalSearch` + scale colore rotting |
| `app/api/console/pipeline/board/route.ts` | GET board (colonne+card) dal gateway |
| `app/api/console/pipeline/set-stage/route.ts` | `write(stage_id)` su `crm.lead` |
| `components/SearchBar.tsx` | Ricerca universale (lead/partner/mail/dossier) |

## Surface 2 — Contatti / Dossier (partner = pivot)
| File | Ruolo |
|---|---|
| `app/partner/[id]/page.tsx` | Route record partner |
| `components/PartnerClient.tsx` | Scheda partner |
| `components/PartnerContext.tsx` | Contesto/aggregazione partner |
| `components/DossierTabs.tsx` | Tab del dossier |
| `components/RelationshipTimeline.tsx` | Timeline relazione partner |
| `components/PartnerMailThread.tsx` | Thread mail del partner |
| `app/dossier/page.tsx` | Indice dossier |
| `lib/bundle.ts` + `app/api/console/partner-bundle/route.ts` | Bundle aggregato partner (lente: read-only multi-modello) |

## Surface 3 — Record Lead (scheda trattativa, PRIORITÀ F1)
| File | Ruolo |
|---|---|
| `app/lead/[id]/page.tsx` | Route record lead; passa `accounts` al client |
| `components/LeadCardClient.tsx` | Scheda lead: header→stepper→4 metriche→azioni→pannelli→timeline; S4 edit-mode (un "Modifica") |
| `components/LeadTimeline.tsx` | Timeline lead (`mail.message`+campionatura+note) |
| `components/LeadOtherMails.tsx` | Altre mail del partner non assegnate (assegnabili) |
| `lib/lead.ts` | Tipi `LeadDetail`/`LeadTimelineItem` + client `getLead`/`getLeadTimeline`/`updateLead` + whitelist edit per ruolo + scale attività |
| `app/api/console/lead/{get,timeline,update,other-mails,assign-mail}/route.ts` | Read/write lead via gateway |
| `components/Composer.tsx` | Composer mail inline (azione "Scrivi mail") |
| `components/{Campionatura,SendDocuments,Ricetta,QuickCreate,SyncMail}Button.tsx` | Azioni native (sale.order is_campione, documenti, cf.task, dossier, sync mail) |

## Note F0 (decisioni)
- **Design system già parzialmente esistente** in `globals.css` (token flat, semantica, 2 pesi 500/600, radius scale). F0 NON riparte da zero: estrae i token in `lib/tokens.ts` (uso TS-side) e consolida gli atomi ricorrenti (chip→`Pill`, iniziali→`Avatar`) in `components/ds/`. Niente nuova libreria UI (vincolo brief).
- **Icone**: set unico già presente (`Icons.tsx`). Nessuna nuova libreria.
- **Inline edit attuale**: pattern S4 "un bottone Modifica → edita tutto → Salva". Il brief F1 chiede edit *per-campo* (click sul campo → edit in place). `InlineEditField` (F1) introdurrà quel pattern riusando la whitelist+`updateLead` esistenti.
- **Right-rail F1** (Opportunità/Campionature/Ordini): dati nativi. Verificare se `partner-bundle` già li espone; altrimenti servono letture read-only aggiuntive sul gateway (consentite dal brief: "solo lettura via JSON-RPC", nessun campo custom nuovo).
