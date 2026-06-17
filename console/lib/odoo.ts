// Client JSON-RPC Odoo — SOLO server-side. Nessun segreto raggiunge il client.
// In mock mode (CONSOLE_USE_MOCK=1 o credenziali assenti) non viene mai contattato Odoo.

const URL = process.env.ODOO_URL ?? "";
const DB = process.env.ODOO_DB ?? "";
const USER = process.env.ODOO_USERNAME ?? "";
const KEY = process.env.ODOO_API_KEY ?? "";

export function shouldUseMock(): boolean {
  if (process.env.CONSOLE_USE_MOCK === "1") return true;
  if (process.env.CONSOLE_USE_MOCK === "0") return false;
  // default: mock se mancano le credenziali
  return !(URL && DB && USER && KEY);
}

type JsonRpcResult = unknown;

async function jsonRpc(path: string, params: Record<string, unknown>): Promise<JsonRpcResult> {
  const res = await fetch(`${URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", method: "call", params, id: Date.now() }),
    // letture: nessuna cache HTTP — la cache è nel bundle layer
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Odoo HTTP ${res.status}`);
  const data = (await res.json()) as { result?: JsonRpcResult; error?: { data?: { message?: string } } };
  if (data.error) throw new Error(`Odoo RPC: ${data.error.data?.message ?? "errore"}`);
  return data.result;
}

let cachedUid: number | null = null;

async function uid(): Promise<number> {
  if (cachedUid) return cachedUid;
  const result = (await jsonRpc("/jsonrpc", {
    service: "common",
    method: "authenticate",
    args: [DB, USER, KEY, {}],
  })) as number | false;
  if (!result) throw new Error("Odoo: autenticazione fallita (db/login/api_key).");
  cachedUid = result;
  return result;
}

/** Chiama un metodo di modello: execute_kw(db, uid, key, model, method, args, kwargs). */
export async function callKw<T = unknown>(
  model: string,
  method: string,
  args: unknown[] = [],
  kwargs: Record<string, unknown> = {},
): Promise<T> {
  const id = await uid();
  return (await jsonRpc("/jsonrpc", {
    service: "object",
    method: "execute_kw",
    args: [DB, id, KEY, model, method, args, kwargs],
  })) as T;
}

export interface SearchReadOpts {
  fields?: string[];
  limit?: number;
  order?: string;
  offset?: number;
}

export async function searchRead<T = Record<string, unknown>>(
  model: string,
  domain: unknown[],
  opts: SearchReadOpts = {},
): Promise<T[]> {
  const kwargs: Record<string, unknown> = {};
  if (opts.fields) kwargs.fields = opts.fields;
  if (opts.limit != null) kwargs.limit = opts.limit;
  if (opts.order) kwargs.order = opts.order;
  if (opts.offset != null) kwargs.offset = opts.offset;
  return callKw<T[]>(model, "search_read", [domain], kwargs);
}

/** Legge un parametro di sistema Odoo (es. casafolino.groq_api_key) lato server. */
export async function getConfigParam(key: string): Promise<string | null> {
  const out = await callKw<string | false>("ir.config_parameter", "get_param", [key]);
  return out === false ? null : out;
}
