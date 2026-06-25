// Helper di lettura Odoo specifici per il wallboard. SOLO read: search_read / read_group.
// Nessun create/write/unlink, mai (vincolo del brief).
import { callKw } from "@/lib/odoo";

/** Valore many2one Odoo: [id, name] | false. */
export type M2O = [number, string] | false;

export function m2oId(v: unknown): number | null {
  return Array.isArray(v) && typeof v[0] === "number" ? v[0] : null;
}
export function m2oName(v: unknown): string | null {
  return Array.isArray(v) && typeof v[1] === "string" ? v[1] : null;
}

export interface ReadGroupRow {
  [key: string]: unknown;
  __count?: number;
  __domain?: unknown;
}

export async function readGroup(
  model: string,
  domain: unknown[],
  fields: string[],
  groupby: string[],
  opts: { orderby?: string; limit?: number } = {},
): Promise<ReadGroupRow[]> {
  const kwargs: Record<string, unknown> = { domain, fields, groupby, lazy: false };
  if (opts.orderby) kwargs.orderby = opts.orderby;
  if (opts.limit != null) kwargs.limit = opts.limit;
  return callKw<ReadGroupRow[]>(model, "read_group", [], kwargs);
}

/** read_group con un solo gruppo che ritorna solo il conteggio totale. */
export async function searchCount(model: string, domain: unknown[]): Promise<number> {
  return callKw<number>(model, "search_count", [domain]);
}
