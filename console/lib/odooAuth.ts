// Verifica identità umana contro Odoo — SOLO per login casafolinoerp (Phase 1 S5).
// VINCOLO ASSOLUTO: queste credenziali umane verificano SOLO l'identità + l'appartenenza
// al gruppo operatori. La sessione/credenziale umana NON diventa MAI la credenziale RPC dati:
// si conserva esclusivamente lo uid (+ name). Tutti gli RPC dati restano su console_api (odoo.ts).
import { shouldUseMock } from "./odoo";

const URL = process.env.ODOO_URL ?? "";
const DB = process.env.ODOO_DB ?? "";

// Allowlist unica: stesso gruppo usato dal gateway per validare operator_uid (Phase 2).
const OPERATOR_GROUP = "casafolino_console_access.group_console_operator";

export interface Operator {
  uid: number;
  name: string;
}

async function rpc(params: Record<string, unknown>): Promise<unknown> {
  const res = await fetch(`${URL}/jsonrpc`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", method: "call", params, id: 1 }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Odoo HTTP ${res.status}`);
  const data = (await res.json()) as { result?: unknown; error?: { data?: { message?: string } } };
  if (data.error) throw new Error(`Odoo RPC: ${data.error.data?.message ?? "errore"}`);
  return data.result;
}

/**
 * Verifica le credenziali Odoo dell'umano e l'appartenenza al gruppo operatori.
 * Ritorna {uid, name} se valido E in allowlist, altrimenti null.
 *
 * Allowlist verificata con le credenziali DELL'UMANO (has_group su self.env.user),
 * NON via console_api → console_api non riceve permessi nuovi su res.users/res.groups.
 * Dopo il check la sessione/credenziale umana viene scartata: torna solo uid+name.
 */
export async function verifyOperator(login: string, password: string): Promise<Operator | null> {
  const l = (login || "").trim();
  if (!l || !password) return null;

  // Dev/mock: nessun Odoo raggiungibile → operatore fittizio (qualsiasi credenziale non vuota).
  if (shouldUseMock()) {
    return { uid: 2, name: `${l} (mock operator)` };
  }

  // 1. authenticate COME L'UMANO (verifica credenziali → uid)
  const uid = (await rpc({
    service: "common",
    method: "authenticate",
    args: [DB, l, password, {}],
  })) as number | false;
  if (!uid) return null; // credenziali errate

  // 2. allowlist: has_group con le credenziali umane (self.env.user = uid).
  // execute_kw interpreta args[0] come ids del recordset → has_group(self, group_ext_id)
  // va chiamato come [[uid], OPERATOR_GROUP] (ids + arg), non [OPERATOR_GROUP].
  const inGroup = (await rpc({
    service: "object",
    method: "execute_kw",
    args: [DB, uid, password, "res.users", "has_group", [[uid], OPERATOR_GROUP]],
  })) as boolean;
  if (!inGroup) return null; // utente Odoo valido ma NON Console Operator → negato

  // 3. name (con le credenziali umane: legge il proprio record)
  let name = l;
  try {
    const recs = (await rpc({
      service: "object",
      method: "execute_kw",
      args: [DB, uid, password, "res.users", "read", [[uid], ["name"]]],
    })) as Array<{ name?: string }>;
    if (recs?.[0]?.name) name = recs[0].name as string;
  } catch {
    /* name è cosmetico: in caso di errore resta il login */
  }

  // sessione/credenziale umana scartata qui — si conserva solo uid+name.
  return { uid, name };
}
