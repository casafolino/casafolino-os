# Inspection: Skill Odoo Pubbliche per Claude Code

**Data analisi**: 2026-04-25  
**Analista**: Claude Code (autonomo, read-only)  
**Repo ispezionati**: 2  
**Skill custom di riferimento**: `casafolino-odoo-deploy`, `casafolino-mail-v2`

---

## 1. Riepilogo Esecutivo

Ispezionati 2 repo open-source con plugin/skill Odoo per Claude Code. Il primo (`ahmed-lakosha/odoo-plugins`) contiene **8 plugin** ben strutturati, attivamente mantenuti (16 commit in 3 mesi), con skills che coprono docker, frontend, report, test, security, i18n, service lifecycle e upgrade — tutti per Odoo 14-19. Il secondo (`stanleykao72/claude-code-spec-workflow-odoo`) è un fork stale (0 commit in 3 mesi, ultimo settembre 2025), installabile via npm, che aggiunge workflow spec/bug strutturati con adattamento Odoo. Richiede `npm i -g` e genera file `.claude/` nella directory progetto. Due conflitti critici identificati: `odoo-docker-plugin` e `odoo-service-plugin` si sovrappongono fortemente a `casafolino-odoo-deploy` con pattern incompatibili (docker-compose vs. sudo cp + manual docker exec). Nessun red flag di sicurezza critico.

---

## 2. Repo 1: ahmed-lakosha/odoo-plugins

### 2a. Metadata e Salute

| Campo | Valore |
|-------|--------|
| Ultimo commit | 2026-03-28 (27 giorni fa) |
| Commit ultimi 3 mesi | 16 |
| Autore principale | a-lakosha |
| Licenza | LGPL-3 ✅ |
| CONTRIBUTING | ❌ Assente |
| SECURITY | ❌ Assente |
| Stato | **Attivo**, mantenuto |

### 2b. Contenuto Dettagliato

| # | Plugin | Path | Skill/Commands | Odoo Versions | Descrizione |
|---|--------|------|----------------|---------------|-------------|
| 1 | **odoo-docker** | `odoo-docker-plugin/` | `/odoo-docker` | 14-19 | Docker infra: compose, nginx, CI/CD, perf tuning, debug container |
| 2 | **odoo-frontend** | `odoo-frontend-plugin/` | `/odoo-frontend`, `/create-theme` | 14-19 | Website theme: publicWidget, OWL, Bootstrap, Figma→Odoo, SCSS |
| 3 | **odoo-report** | `odoo-report-plugin/` | `/odoo-report`, 7 sotto-comandi | 14-19 | QWeb PDF reports, email template, wkhtmltopdf, bilingual |
| 4 | **odoo-test** | `odoo-test-plugin/` | `/odoo-test`, 4 sotto-comandi | 14-19 | Test skeleton, mock data, coverage, Playwright e2e |
| 5 | **odoo-security** | `odoo-security-plugin/` | `/odoo-security`, 4 sotto-comandi | 14-19 | Audit ACL, routes, sudo(), SQL injection, risk score |
| 6 | **odoo-i18n** | `odoo-i18n-plugin/` | `/odoo-i18n` | 14-19 | Traduzioni .po, estrazione, RTL/Arabic |
| 7 | **odoo-service** | `odoo-service-plugin/` | `/odoo-service` | 14-19 | Server lifecycle: start/stop, DB backup, venv, Docker, IDE config |
| 8 | **odoo-upgrade** | `odoo-upgrade-plugin/` | `/odoo-upgrade`, 2 sotto-comandi | 14-19 | Migrazione moduli tra versioni, 150+ pattern, auto-fix |

### 2c. Analisi Sicurezza

| Pattern cercato | Trovato | Dettaglio |
|----------------|---------|-----------|
| `rm -rf /` (distruttivo) | ❌ No | Solo `rm -rf /var/lib/apt/lists/*` in Dockerfile template (standard) |
| `curl \| bash` | ⚠️ 1 | `odoo-docker-plugin/templates/Dockerfile.template:77` — `curl -fsSL https://deb.nodesource.com/setup_20.x \| bash -` (standard per Node.js in Dockerfile, non eseguito direttamente) |
| `curl \| sh` | ❌ No | |
| `chmod +x` + exec | ⚠️ 1 | `Dockerfile.template:113` — `chmod +x /opt/odoo/entrypoint.sh` (standard Docker) |
| `subprocess shell=True` | ❌ No | |
| `wget` + exec | ❌ No | |
| Credential requirement | ⚠️ | `odoo-test` Playwright patterns reference `ODOO_PASSWORD` env var (documentation only, non eseguito automaticamente) |
| Install scripts | ❌ | Nessun `setup.sh` o `install.sh`. Plugin sono pure Claude Code skills (copia files) |

**Verdetto sicurezza**: ✅ Nessun rischio. Pattern trovati sono standard Docker template (non eseguiti durante install plugin) e documentazione Playwright.

### 2d. Analisi Compatibilità con Custom Skills

#### odoo-docker-plugin vs casafolino-odoo-deploy

| Aspetto | odoo-docker (generico) | casafolino-odoo-deploy (custom) | Conflitto? |
|---------|----------------------|-------------------------------|------------|
| Deploy flow | `docker-compose up -d`, `docker-compose build` | `sudo cp -rf` + `docker exec odoo -u` + `docker restart` | **🔴 CONFLITTO CRITICO** |
| Config | Genera `docker-compose.yml`, `.env`, `nginx.conf` | Non usa docker-compose (container gestiti manualmente) | 🔴 Incompatibile |
| DB management | `docker-compose exec` pattern | `docker exec odoo-app` direttamente | 🟡 Diverso naming |
| Trigger | Automatico su topic "Docker + Odoo" | Automatico su topic "deploy + Odoo" | 🔴 Sovrapposizione trigger |

**Rischio**: Se entrambe attive, un prompt tipo "deploya casafolino_mail" potrebbe triggerare `odoo-docker` che suggerisce `docker-compose build` — **rompendo il workflow certificato**.

#### odoo-service-plugin vs casafolino-odoo-deploy

| Aspetto | odoo-service (generico) | casafolino-odoo-deploy (custom) | Conflitto? |
|---------|------------------------|-------------------------------|------------|
| Server start/stop | `odoo-bin` diretto o `docker-compose` | `docker restart odoo-app` | 🔴 Conflitto |
| DB backup | `pg_dump` via venv/docker-compose | `docker exec -e PGPASSWORD=odoo odoo-app pg_dump -h odoo-db` | 🟡 Diverso pattern |
| Module scaffold | Generico, crea struttura standard | Non coperto | ✅ No conflitto |
| Environment init | Crea venv, installa requirements | Non applicabile (Docker) | 🟡 Non rilevante |

#### odoo-security-plugin vs custom skills

**Nessun conflitto.** Complementare — audita modelli, ACL, sudo(), SQL injection. Non tocca deploy flow.

#### odoo-test-plugin vs custom skills

**Nessun conflitto.** Complementare — genera test, mock data, coverage. Non tocca deploy flow.

#### odoo-report-plugin vs custom skills

**Nessun conflitto.** CasaFolino non ha skill per report QWeb. Complementare.

#### odoo-frontend-plugin vs custom skills

**Nessun conflitto diretto.** CasaFolino usa OWL per `casafolino_mail` ma senza skill dedicata frontend. Potenzialmente utile per pattern OWL/publicWidget, ma rischio basso di contraddizione su regole CSS (il plugin suggerisce Google Fonts in alcuni template, CLAUDE.md vieta `@import url()`).

#### odoo-i18n-plugin vs custom skills

**Nessun conflitto.** CasaFolino è monolingua (IT) attualmente. Non rilevante ora.

#### odoo-upgrade-plugin vs custom skills

**Nessun conflitto.** CasaFolino è su Odoo 18, non sta migrando. Non rilevante ora.

### 2e. Raccomandazione per Plugin

| Plugin | Categoria | Giustificazione |
|--------|-----------|----------------|
| **odoo-security** | **INSTALL NOW** | Zero conflitti. Audita ACL, sudo(), SQL injection. Valore immediato per casafolino_mail (usa `cr.execute()` diretto e `sudo()` in diversi punti). |
| **odoo-test** | **INSTALL NOW** | Zero conflitti. Genera test skeleton per i modelli custom. CasaFolino non ha test suite. |
| **odoo-report** | **INSTALL LATER** | Nessun conflitto ma non urgente. CasaFolino non sviluppa report QWeb attualmente. Installare quando serve. |
| **odoo-frontend** | **INSTALL PARTIAL** | Skills `frontend-js` e `theme-scss` utili per OWL pattern. Ma `theme-create` e `theme-design` non rilevanti. ⚠️ Verificare che non suggerisca Google Fonts (vietato da CLAUDE.md). |
| **odoo-i18n** | **DO NOT INSTALL** | CasaFolino monolingua IT. Nessuna esigenza i18n. Aggiunge complessità inutile. |
| **odoo-docker** | **DO NOT INSTALL** | Conflitto critico con `casafolino-odoo-deploy`. Assume `docker-compose` — CasaFolino usa container manuali con `sudo cp + docker exec`. Rischio di corrompere il deploy flow certificato. |
| **odoo-service** | **DO NOT INSTALL** | Conflitto con `casafolino-odoo-deploy` su server lifecycle. Pattern `odoo-bin` e `docker-compose exec` incompatibili con setup CasaFolino. |
| **odoo-upgrade** | **DO NOT INSTALL** | Odoo 18 stabile, nessuna migrazione in corso. Riservare per eventuale migrazione 18→19. |

---

## 3. Repo 2: stanleykao72/claude-code-spec-workflow-odoo

### 3a. Metadata e Salute

| Campo | Valore |
|-------|--------|
| Ultimo commit | 2025-09-02 (~8 mesi fa) |
| Commit ultimi 3 mesi | 0 |
| Autore principale | Stanley Kao |
| Licenza | MIT ✅ |
| CONTRIBUTING | ❌ Assente |
| SECURITY | ❌ Assente |
| Fork di | [Pimzino/claude-code-spec-workflow](https://github.com/Pimzino/claude-code-spec-workflow) |
| Stato | **Stale / Abbandonato** |

### 3b. Contenuto Dettagliato

| Componente | Cosa fa |
|-----------|---------|
| Slash commands (10) | `/odoo-spec-create`, `/odoo-spec-execute`, `/odoo-spec-list`, `/odoo-spec-status`, `/odoo-steering`, `/odoo-bug-create`, `/odoo-bug-analyze`, `/odoo-bug-fix`, `/odoo-bug-status`, `/odoo-bug-verify` |
| Agents (4) | spec-design-validator, spec-requirements-validator, spec-task-executor, spec-task-validator (+ varianti Odoo) |
| Templates (5) | odoo-requirements, odoo-design, odoo-tasks, odoo-product, odoo-cleanup-policy |
| Dashboard | Real-time web dashboard (TypeScript, Tauri desktop app) |
| Odoo integration | Version detection 14-18, module management, environment support (Docker, local, Odoo.sh) |
| Tunnel feature | Cloudflare/ngrok tunnel per accesso remoto dashboard |

**Installazione richiede**: `npm i -g @stanleykao72/claude-code-spec-workflow-odoo` + `npx ... setup` + `npx ... odoo-setup`. Genera files in `.claude/` e `.odoo-dev/` nella directory progetto.

### 3c. Analisi Sicurezza

| Pattern cercato | Trovato | Dettaglio |
|----------------|---------|-----------|
| `rm -rf` | ❌ No | |
| `curl \| bash` | ❌ No | |
| `chmod +x` | ⚠️ 1 | `scripts/fix-permissions.js:24` — sets executable bit on cli.js (standard npm post-install) |
| `subprocess` | ❌ No (TypeScript, non Python) | |
| Credential requirement | ❌ No | Solo autenticazione Odoo per e2e test (opzionale) |
| Install scripts | ⚠️ | `npm i -g` installa globalmente, `setup` genera file in `.claude/` e `.odoo-dev/` |

**Verdetto sicurezza**: ✅ Nessun rischio intrinseco. Ma `npm i -g` installa pacchetti npm globali con `postinstall` hook.

### 3d. Analisi Compatibilità con Custom Skills

| Aspetto | spec-workflow-odoo | Skill CasaFolino | Conflitto? |
|---------|-------------------|------------------|------------|
| Workflow spec | Requirements→Design→Tasks→Implementation | GSD (plan-phase, execute-phase, verify-work) | 🔴 **Sovrapposizione massiva** con GSD |
| Bug workflow | Report→Analyze→Fix→Verify | GSD debug + code-review | 🔴 Sovrapposizione con `/gsd-debug` |
| File `.claude/` | Genera comandi custom in `.claude/commands/` | CLAUDE.md + GSD skills già presenti | 🟡 Potenziale merge conflict |
| Odoo version detect | Auto-detect 14-18 | Non coperto dalle custom skills | ✅ Feature unica |
| Dashboard | Web dashboard locale | Non coperto | ✅ Feature unica ma non necessaria |

**Rischio critico**: Il workflow spec è una duplicazione quasi completa di GSD. Installarlo creerebbe confusione su quale workflow seguire (GSD o spec-workflow).

### 3e. Raccomandazione

| Componente | Categoria | Giustificazione |
|-----------|-----------|----------------|
| **Intero pacchetto** | **DO NOT INSTALL** | Stale (8 mesi senza commit), duplica GSD workflow già in uso, richiede `npm i -g` con postinstall hooks, genera file in `.claude/` che potrebbero confliggere con setup esistente. Nessuna feature unica che giustifichi il rischio. |

---

## 4. Piano di Installazione Proposto

### Skill da installare (INSTALL NOW)

#### 1. odoo-security (priorità alta)

```bash
# Installazione
# Opzione A: come plugin Claude Code (se supportato)
cd /Users/antoniofolino/casafolino-os
claude mcp add odoo-security https://github.com/ahmed-lakosha/odoo-plugins.git --subdir odoo-security-plugin

# Opzione B: copia manuale come skill utente
cp -r /tmp/skill-inspection/odoo-plugins/odoo-security-plugin/odoo-security \
  ~/.claude/skills/user/odoo-security

# Disinstallazione in caso di problemi
rm -rf ~/.claude/skills/user/odoo-security
# oppure
claude mcp remove odoo-security
```

**Verifica post-installazione**:
- [ ] `claude` → `/odoo-security` risponde senza errori
- [ ] Non interferisce con `/gsd-*` commands
- [ ] Prompt "deploya casafolino_mail" invoca ancora `casafolino-odoo-deploy` (non security)
- [ ] `ls ~/.claude/skills/user/` mostra 3 skill (deploy + mail-v2 + security)

#### 2. odoo-test (priorità media)

```bash
# Installazione
cp -r /tmp/skill-inspection/odoo-plugins/odoo-test-plugin/odoo-test \
  ~/.claude/skills/user/odoo-test

# Disinstallazione
rm -rf ~/.claude/skills/user/odoo-test
```

**Verifica post-installazione**:
- [ ] `claude` → `/odoo-test` risponde senza errori
- [ ] Non interferisce con skill esistenti
- [ ] Prompt "genera test per casafolino_mail" attiva `odoo-test` correttamente

### Ordine di installazione raccomandato

1. **odoo-security** — valore immediato, zero rischio
2. **odoo-test** — valore medio, zero rischio
3. (Futuro) **odoo-report** — quando servono report QWeb
4. (Futuro) **odoo-frontend** (solo skills `frontend-js` + `theme-scss`) — quando si tocca OWL

---

## 5. Piano di Esclusione

| Skill/Plugin | Categoria | Motivazione |
|-------------|-----------|-------------|
| **odoo-docker** | DO NOT INSTALL | Conflitto critico: assume `docker-compose`, CasaFolino usa `sudo cp + docker exec + docker restart` manuale. Potrebbe corrompere deploy flow certificato se triggerato su prompt ambigui. |
| **odoo-service** | DO NOT INSTALL | Conflitto: pattern `odoo-bin` e `docker-compose exec` incompatibili con infrastruttura CasaFolino. |
| **odoo-i18n** | DO NOT INSTALL | Non rilevante: CasaFolino monolingua IT. Nessuna roadmap i18n. |
| **odoo-upgrade** | DO NOT INSTALL | Non rilevante ora: Odoo 18 stabile. Rivalutare solo pre-migrazione 18→19. |
| **spec-workflow-odoo** (intero repo) | DO NOT INSTALL | Stale (8 mesi), duplica GSD già in uso, `npm i -g` invasivo, genera file in `.claude/` con rischio conflitto. |

---

## 6. Sommario Numerico

| Metrica | Valore |
|---------|--------|
| Repo clonati | 2 |
| Skill/plugin ispezionate | 9 (8 da odoo-plugins + 1 pacchetto spec-workflow) |
| INSTALL NOW | **2** (odoo-security, odoo-test) |
| INSTALL LATER | **1** (odoo-report) |
| INSTALL PARTIAL | **1** (odoo-frontend, solo 2 sub-skills su 5) |
| DO NOT INSTALL | **5** (odoo-docker, odoo-service, odoo-i18n, odoo-upgrade, spec-workflow) |
| Red flag sicurezza | **0** (pattern trovati sono standard Docker template) |
| Conflitti compatibilità | **3** (odoo-docker vs deploy, odoo-service vs deploy, spec-workflow vs GSD) |
