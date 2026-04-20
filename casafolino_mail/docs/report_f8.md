# Report F8 — Composer Outlook-style + Template WYSIWYG

**Modulo:** casafolino_mail 18.0.8.7.0
**Branch:** feat/mail-v3-f8
**Base:** fix/mail-v3-f7 (18.0.8.6.0)
**Data:** 2026-04-20

---

## Feature Composer Outlook-style

### Rich Toolbar (AC2)
Sostituzione textarea con `contenteditable` div + toolbar completa:
- **Formattazione**: Bold, Italic, Underline, Strikethrough
- **Font**: Size selector (8-36pt via 7 livelli execCommand)
- **Colori**: Font color + background color (24 colori palette CasaFolino)
- **Liste**: Ordered, Unordered, Indent, Outdent
- **Allineamento**: Left, Center, Right, Justify
- **Inserimento**: Link, Horizontal Rule
- **Utility**: Remove Format, Undo, Redo

### Emoji Picker (AC3, AC4)
- 50 emoji business-relevant (smileys, handshake, flags IT/DE/GB/ES/FR, food, charts)
- Search bar per filtraggio rapido per keyword
- Insert alla posizione cursore via `insertText`
- Lazy: popup solo su click bottone toolbar

### Inline Image Drag & Drop (AC5, AC6)
- Immagini (image/*) dragged → upload server → `<img src="/web/image/{id}">` inline
- File non-image (PDF, Word) → attachment standard (comportamento invariato)
- Supporto paste immagini da clipboard

### Firma Inline (AC7)
- Firma default account visibile in fondo al body, editabile
- Separatore visivo `<hr>` con stile inline
- Re-append dopo cambio template

### Autosave Indicator (AC8)
- Debounce 15 secondi su ogni modifica body/subject
- Label footer: "Bozza salvata alle HH:MM"
- Spinner durante salvataggio, warning su errore
- Timer periodico 15s in background

---

## Feature Template Management

### Template Selector Panel (AC9, AC10, AC11, AC12, AC13)
- Panel laterale SX collapsible (default aperto su "Nuovo messaggio")
- Lista template con badge lingua (flag emoji) + badge categoria
- Search bar: filtra per nome, subject, categoria
- Dropdown filtro lingua (Tutte/IT/EN/DE/ES/FR)
- Hover → tooltip preview body renderizzato (200px max)
- Click → applica template (prefill subject+body) e chiude panel

### Auto-detect Lingua (AC14)
- Endpoint `/cf/mail/v3/partner/detect_language`
- Mappa `COUNTRY_TO_LANG`: IT/SM/VA→it_IT, DE/AT/CH/LI→de_DE, ES/MX/AR/CL/CO/PE→es_ES, FR/BE/LU/MC/CA→fr_FR
- Default: en_US
- Template panel pre-filtrato su lingua rilevata
- Badge "Suggerito" su template matching

### Preview Modal (AC15)
- Bottone "Anteprima" in header composer
- Modal con: Da, A, Oggetto, Body renderizzato
- Chiusura click overlay o bottone Chiudi

### Template Form WYSIWYG (AC16)
- `body_html` widget="html" con options enhanced
- Sezione variabili aggiornata con 25+ variabili raggruppate per categoria

---

## Nuove Variabili Disponibili (AC17)

### Partner extra (3)
| Variabile | Descrizione |
|-----------|-------------|
| `{{partner_full_address}}` | Via, Citta, Stato, Paese |
| `{{partner_vat}}` | Partita IVA |
| `{{partner_company_type}}` | Azienda/Persona |

### Sales extra (3)
| Variabile | Descrizione |
|-----------|-------------|
| `{{total_orders_ytd}}` | Conteggio ordini anno corrente |
| `{{total_revenue_ytd}}` | Totale fatturato YTD (formattato) |
| `{{top_product}}` | Prodotto piu ordinato |

### Thread extra (3)
| Variabile | Descrizione |
|-----------|-------------|
| `{{thread_message_count}}` | Numero messaggi nel thread |
| `{{thread_first_email_date}}` | Data prima email thread |
| `{{thread_attachment_count}}` | Numero allegati nel thread |

### Account extra (3)
| Variabile | Descrizione |
|-----------|-------------|
| `{{account_email}}` | Email account mittente |
| `{{account_signature_name}}` | Nome firma utente corrente |
| `{{account_manager_name}}` | Assegnatario CRM del partner |

### Utilities (3)
| Variabile | Descrizione |
|-----------|-------------|
| `{{current_season}}` | primavera/estate/autunno/inverno |
| `{{months_since_last_contact}}` | Mesi dall'ultimo contatto |
| `{{partner_time_zone}}` | Timezone partner |

---

## 10 Template Default Aggiunti (AC18)

| # | Nome | Lingua | Categoria |
|---|------|--------|-----------|
| 1 | Invio listino prodotti | IT | quote |
| 2 | Conferma ordine e spedizione | IT | follow_up |
| 3 | Price list shipment | EN | quote |
| 4 | Order confirmation | EN | follow_up |
| 5 | Sample follow-up after 2 weeks | EN | follow_up |
| 6 | Musteranfrage Follow-up | DE | follow_up |
| 7 | Preisliste | DE | quote |
| 8 | Envio de catalogo | ES | quote |
| 9 | Seguimiento post-feria | ES | post_fair |
| 10 | Envoi catalogue | FR | quote |

---

## AC Coverage

| AC | Descrizione | Status |
|----|-------------|--------|
| AC1 | Module 18.0.8.6.0 → 18.0.8.7.0 senza ERROR | DONE |
| AC2 | Toolbar composer B/I/U/S/font/color/list/align/link/undo | DONE |
| AC3 | Click emoji in toolbar apre picker | DONE |
| AC4 | Select emoji inserisce a posizione cursore | DONE |
| AC5 | Drag immagine → inline img tag | DONE |
| AC6 | Drag file non-image → attachment | DONE |
| AC7 | Firma inline editabile | DONE |
| AC8 | Indicatore "Bozza salvata alle HH:MM" | DONE |
| AC9 | Panel laterale template, collapsible | DONE |
| AC10 | Hover template → preview body | DONE |
| AC11 | Click template → applica + chiude panel | DONE |
| AC12 | Search bar filtra template | DONE |
| AC13 | Badge lingua + categoria | DONE |
| AC14 | Auto-detect lingua da partner | DONE |
| AC15 | Anteprima finale modal | DONE |
| AC16 | Template form WYSIWYG | DONE |
| AC17 | 15 variabili nuove | DONE |
| AC18 | 10 template precaricati | DONE |

**18/18 AC completati.**

---

## File Modificati

| File | Tipo |
|------|------|
| `static/src/js/mail_v3/mail_v3_compose.js` | Rewrite completo |
| `static/src/xml/mail_v3/mail_v3_compose.xml` | Rewrite completo |
| `static/src/scss/mail_v3.scss` | Sezione compose riscritta + nuove sezioni |
| `controllers/mail_v3_controllers.py` | +3 endpoint (templates/list, template/preview, detect_language) |
| `models/casafolino_mail_template.py` | _build_variables espanso (25+ var) |
| `views/mail_template_views.xml` | Variable reference aggiornata |
| `data/mail_v3_templates_seed.xml` | 10 template nuovi |
| `__manifest__.py` | Version bump + data file |

---

## Raccomandazioni F9

1. **WhatsApp Integration** — Bottone "Invia su WhatsApp" nel composer, link a wa.me/ con body pre-compilato
2. **Calendar Integration** — Proponi meeting da thread, crea evento Google Calendar / Odoo Calendar
3. **Multi-lingua UI switcher** — Label UI in IT/EN/DE per utenti internazionali
4. **Voice-to-text** — Dettatura vocale nel composer (Web Speech API)
5. **Template analytics** — Dashboard uso template, conversion rate per template
6. **Firma WYSIWYG editor** — Editor firma dedicato con logo upload e preview
7. **CC/BCC auto-suggest** — Suggerisci CC basato su thread history
8. **Attachment preview** — Preview inline di PDF e immagini prima dell'invio
