# BUG B -- Scroll infinito non funziona in "La Mia Casella"

**Data analisi**: 2026-04-25
**Stato**: Diagnosi completata, fix NON implementato

---

## Sintomo

Lo scroll infinito nella lista thread ("Conversazioni") non carica ulteriori email. L'utente scorre fino in fondo, ma non vengono caricate nuove pagine, oppure il caricamento si blocca.

---

## Componente JS identificato

- **File**: `casafolino_mail/static/src/js/mail_v3/mail_v3_thread_list.js`
- **Classe**: `ThreadList` (OWL Component)
- **Template**: `casafolino_mail/static/src/xml/mail_v3/mail_v3_thread_list.xml`
- **Parent**: `MailV3Client` in `casafolino_mail/static/src/js/mail_v3/mail_v3_client.js`

---

## Endpoint backend identificato

- **Route**: `POST /cf/mail/v3/threads/list` (type='json', auth='user')
- **File**: `casafolino_mail/controllers/mail_v3_controllers.py`, linea 51
- **Metodo**: `threads_list(**kw)`
- **Parametri**: `account_ids`, `state`, `limit` (default 50, max 200), `offset`, `filters`, `folder`

---

## Analisi del flusso scroll

### 1. Trigger: scroll event listener

`ThreadList.setup()` aggiunge un event listener `scroll` su `this.listRef.el` (ref="threadListContainer").

Condizione di trigger (linea 30):
```
el.scrollTop + el.clientHeight >= el.scrollHeight - 200
```
Quando l'utente e' a 200px dal fondo, chiama `this.props.onLoadMore()` SE `props.hasMore && !props.loadingMore`.

### 2. Elemento scrollabile

Nel template XML, `t-ref="threadListContainer"` e' su `<div class="mv3-thread-list__scroll">` (linea 17 del template).

### 3. Gestione stato nel parent (MailV3Client)

- `loadThreads()` (linea 145): resetta `threadsOffset=0`, `hasMoreThreads=false`, fa RPC con `offset=0`, poi setta `threadsOffset = threads.length`
- `loadMoreThreads()` (linea 170): guard `loading.threadsMore || !hasMoreThreads`. Fa RPC con `offset=state.threadsOffset`. Appende risultati, incrementa offset.

### 4. Backend: calcolo `has_more`

**Linea 235 del controller**:
```python
has_more = (offset + len(result)) < total
```

---

## BUG PRINCIPALE IDENTIFICATO: Dismissed sender filtering rompe la paginazione

### Evidenza dal codice (controller linee 190-206)

Il backend:
1. Esegue `search(domain, limit=50, offset=X)` -- il DB restituisce esattamente 50 record
2. Itera i 50 record e SCARTA i thread in cui tutti i mittenti inbound sono "dismissed" (linea 205-206: `continue`)
3. Calcola `has_more = (offset + len(result)) < total`

Il problema: `total` viene da `search_count(domain)` che conta TUTTI i thread (inclusi quelli dismissed), ma `len(result)` contiene solo i thread NON dismissed. Questo causa **due bug distinti**:

### Bug B.1 -- `has_more` diventa `false` prematuramente

Esempio concreto:
- DB ha 120 thread che matchano il domain
- `total = 120`
- Prima pagina: `offset=0`, DB torna 50 record, ma 10 hanno mittenti dismissed -> `result` ha 40 thread
- `has_more = (0 + 40) < 120` = `true` -- OK fin qui
- `threadsOffset` nel frontend viene settato a `40` (len di threads)
- Seconda pagina: `offset=40`, DB torna 50 record (dal 41 al 90), 15 dismissed -> `result` ha 35
- `has_more = (40 + 35) < 120` = `true`
- `threadsOffset = 40 + 35 = 75`
- Terza pagina: `offset=75`, ma il DB inizia dal record 76 (non dal 76esimo non-dismissed!). Il backend ha gia' servito i record 1-90 al DB, ma il frontend pensa di essere al record 75. **L'offset e' disallineato**.

### Bug B.2 -- Thread duplicati o mancanti

Poiche' il frontend manda `offset = numero_di_thread_ricevuti` (non l'offset reale del DB), e il backend usa quell'offset direttamente nella `search()`, ci sara' un gap. Thread dal 41 al 50 (offset 40-49 nel DB) verranno saltati, oppure thread gia' visti verranno ripetuti.

### Bug B.3 -- Il contatore "total" e' gonfiato

`total` include i thread dismissed, quindi il conteggio "(120)" mostrato nell'header della lista e' sbagliato.

---

## Scenario di CSS: Confermato funzionante

Il container scrollabile `mv3-thread-list__scroll` ha:
- `flex: 1` + `overflow-y: auto` (SCSS linea 1915-1918)
- Il parent `.mv3-thread-list` ha `flex: 1` + `overflow-y: auto` (SCSS linea 304-306)
- Il grandparent `.mv3-client__thread-list` ha `overflow-y: auto` (linea 34)

**Potenziale problema secondario**: ci sono DUE livelli di `overflow-y: auto` annidati (`.mv3-client__thread-list` e `.mv3-thread-list`). Se `.mv3-thread-list` si espande naturalmente dentro `.mv3-client__thread-list`, lo scroll event listener su `mv3-thread-list__scroll` potrebbe non triggerare mai perche' e' il parent che scrolla, non il ref. Tuttavia, il bug principale resta quello della paginazione backend.

---

## Scenari di fallimento classificati

| # | Scenario | Probabilita' | Evidenza |
|---|----------|-------------|----------|
| 1 | Trigger non scatta (CSS nesting) | Media | Due overflow-y:auto annidati |
| 2 | RPC fallisce silenziosamente | Bassa | Catch con console.error presente |
| 3 | RPC torna 0 risultati (offset sbagliato) | **ALTA** | Offset disallineato da filtering dismissed |
| 4 | Risultati non appesi allo state | Bassa | Spread operator corretto |
| 5 | Risultati duplicati | **ALTA** | Offset frontend != offset DB reale |
| 6 | Loading guard bloccata | Bassa | Guard resettata in finally |

---

## Azioni di conferma richieste all'utente

1. **Aprire la console browser** su La Mia Casella, scrollare fino in fondo, e verificare se appare `[mail v3] loadMoreThreads error:` oppure se la RPC non parte proprio (nessun network request in tab Network)
2. **Verificare quanti mittenti dismissed** ci sono nel sistema -- se ce ne sono molti, il bug di paginazione e' quasi certo
3. **Contare** il numero di thread visibili vs il numero mostrato nell'header "(N)" -- se N e' molto piu' alto dei thread effettivamente visibili dopo full scroll, conferma il bug del total gonfiato

---

## Ipotesi di fix (NON implementato)

### Fix A -- Filtrare dismissed nel domain SQL (raccomandato)

Invece di filtrare in Python dopo la query, aggiungere un campo computed o una subquery che escluda i thread dismissed direttamente nel domain prima della `search()`. Questo risolve paginazione, total, e performance in un colpo solo.

Approccio:
1. Costruire la lista di dismissed emails PRIMA della search (gia' fatto alle linee 80-87)
2. Trovare gli ID dei thread da escludere con una query dedicata
3. Aggiungere `('id', 'not in', dismissed_thread_ids)` al domain
4. Rimuovere il `continue` nel loop

### Fix B -- Offset correttivo (workaround)

Cambiare il frontend per mandare il "DB offset" separato dal conteggio thread ricevuti. Il backend dovrebbe tornare `next_offset` esplicito nel response.

### Fix C -- CSS nesting (complementare)

Rimuovere `overflow-y: auto` da `.mv3-thread-list` (linea 306 SCSS) e lasciarlo solo su `.mv3-thread-list__scroll`, oppure rimuovere `overflow-y: auto` da `.mv3-client__thread-list` (linea 34) per evitare che lo scroll avvenga sul container sbagliato.
