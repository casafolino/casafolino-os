// Wallboard — separazione dati per reparto (REQUISITO DI SICUREZZA, server-side).
//
// Ogni monitor kiosk apre una scena con un token-scena in querystring (?k=<token>).
// Il token mappa a uno scope ∈ {production, vetrina, ufficio}. Ogni endpoint /api/wb/*
// dichiara gli scope ammessi: se lo scope del token non è ammesso → HTTP 403, nessun dato.
//
// Conseguenza: un monitor in produzione (scope `production`) NON può ottenere fatturato
// o pipeline nemmeno manipolando URL o devtools — il rifiuto è server-side, non cosmetico.
import { shouldUseMock } from "@/lib/odoo";

export type Scope = "production" | "vetrina" | "ufficio" | "logistica" | "direzione";

export const ALL_SCOPES: Scope[] = ["production", "vetrina", "ufficio", "logistica", "direzione"];

/** Endpoint → scope ammessi. Single source of truth lato server. */
export const ENDPOINT_SCOPES: Record<string, Scope[]> = {
  "production-queue": ["production", "ufficio", "logistica"],
  "mrp-active": ["production", "ufficio"],
  "tasks-today": ["production"],
  "shipments-today": ["production", "vetrina", "logistica"],
  "qc-blocks": ["production"],
  "export-countries": ["vetrina", "ufficio"],
  certifications: ["vetrina"],
  "next-fair": ["vetrina", "ufficio"],
  ticker: ["vetrina", "ufficio"],
  "revenue-mtd": ["vetrina", "ufficio", "direzione"], // MAI production/logistica
  pipeline: ["ufficio"], // SOLO ufficio
  // V2 — azionabilità
  "daily-goal": ["production", "logistica", "ufficio"],
  cutoffs: ["logistica", "ufficio", "direzione"],
  exceptions: ["direzione", "ufficio"], // pannello eccezioni — mai production/logistica/vetrina
};

/** token-scena (da env, generati casuali, mai committati) → scope. */
function tokenMap(): Record<string, Scope> {
  const map: Record<string, Scope> = {};
  const prod = process.env.WB_TOKEN_PROD;
  const vetrina = process.env.WB_TOKEN_VETRINA;
  const ufficio = process.env.WB_TOKEN_UFFICIO;
  const logistica = process.env.WB_TOKEN_LOGISTICA;
  const direzione = process.env.WB_TOKEN_DIREZIONE;
  if (prod) map[prod] = "production";
  if (vetrina) map[vetrina] = "vetrina";
  if (ufficio) map[ufficio] = "ufficio";
  if (logistica) map[logistica] = "logistica";
  if (direzione) map[direzione] = "direzione";
  return map;
}

/**
 * Risolve un token → scope.
 * - In prod (env token impostati): match esatto col token segreto.
 * - In mock mode SENZA token env: accetta i nomi scope letterali ("production"/"vetrina"/
 *   "ufficio") come token di sviluppo, così le scene sono testabili in locale.
 *   Questo fallback è attivo SOLO quando shouldUseMock() è true: in prod reale non leak.
 */
export function scopeForToken(token: string | null | undefined): Scope | null {
  const tok = (token ?? "").trim();
  if (!tok) return null;
  const map = tokenMap();
  if (map[tok]) return map[tok];
  if (Object.keys(map).length === 0 && shouldUseMock()) {
    if ((ALL_SCOPES as string[]).includes(tok)) return tok as Scope;
  }
  return null;
}

/** Estrae il token da una Request: querystring ?k=, poi header x-wb-token. */
export function tokenFromRequest(req: Request): string | null {
  const url = new URL(req.url);
  const k = url.searchParams.get("k");
  if (k) return k;
  return req.headers.get("x-wb-token");
}

export type GuardResult =
  | { ok: true; scope: Scope }
  | { ok: false; status: number; message: string };

/**
 * Guard server-side per gli handler /api/wb/<endpoint>.
 * Ritorna lo scope se il token è valido E ammesso per quell'endpoint, altrimenti
 * un esito di errore (401 token assente/non valido, 403 scope non ammesso).
 */
export function guard(req: Request, endpoint: string): GuardResult {
  const allowed = ENDPOINT_SCOPES[endpoint];
  if (!allowed) return { ok: false, status: 404, message: "endpoint sconosciuto" };
  const scope = scopeForToken(tokenFromRequest(req));
  if (!scope) return { ok: false, status: 401, message: "token-scena assente o non valido" };
  if (!allowed.includes(scope)) {
    return { ok: false, status: 403, message: `scope '${scope}' non ammesso per ${endpoint}` };
  }
  return { ok: true, scope };
}
