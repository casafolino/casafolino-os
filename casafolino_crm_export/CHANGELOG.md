# Changelog — casafolino_crm_export

## v18.0.5.0.0 — Pipeline Operatore-Centrico (2026-05-02)

### Nuova architettura
- Pipeline unica del reparto commerciale, filtrata per operatore (Antonio, Josefina)
- Rimossi 6 menu per mercato (America, Europa, Italia, Medio Oriente, Australia, Altri)
- Aggiunti 2 menu operatore con dominio su `user_id.login`

### 9 Stage uniformi
- Primo Contatto → Interesse → Trattativa → Preventivo → Campionatura → Negoziazione → Vinta / Persa / Standby
- Campo `cf_probability_default` su `crm.stage`: probabilità auto-assegnata al cambio stage
- Stage Standby: mantiene probabilità corrente, fold=True

### Tag al posto di Selection
- `cf_market` e `cf_channel` (campi Selection) migrati a `crm.tag` standard (M2M `tag_ids`)
- 6 tag Mercato (color blu) + 7 tag Canale (color arancio) pre-popolati
- Migration idempotente: preserva tag esistenti, crea solo se mancanti
- Colonne `cf_market`/`cf_channel` droppate post-migrazione

### Cron Auto-Standby
- Cron giornaliero: sposta in Standby i lead senza contatto da 30+ giorni
- Creato via `post_init_hook` (non XML) — conforme regole Odoo 18
- Messaggi nel chatter, nessuna notifica email

### Reset timer `cf_date_last_contact`
- Email in entrata/uscita → aggiorna `cf_date_last_contact`
- Attività completata → aggiorna `cf_date_last_contact`
- Uscita da Standby (cambio stage manuale) → aggiorna `cf_date_last_contact`

### Colore operatore (kanban)
- Bordo sinistro card kanban colorato per operatore:
  - Antonio: verde `#3F8A4F`
  - Josefina: viola `#8B5CF6`
  - Martina: marrone `#6B4A1E`
  - Altri: grigio `#D1D5DB`

### Migration `migrations/18.0.5.0.0/post-migrate.py`
- Mappatura stage vecchi → nuovi con spostamento lead
- Conversione `cf_market`/`cf_channel` → tag con inserimento M2M
- Drop colonne obsolete da `crm_lead` e `cf_export_sample`
- Completamente idempotente (safe per `-u` ripetuti)
