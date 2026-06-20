// POST /api/console/triage { ids:number[], state } → gateway console_triage (bulk).
// operator_uid PRESO DALLA SESSIONE server-side (anti-spoof: body non può fornirlo).
// Solo state via gateway sudo+audit; MAI unlink/write raw. Multi-casella: ogni msg
// mantiene la sua account_id (lo state è per-riga).
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

// Stati che la console può applicare: tieni/scarta/cestina + restore (undo/ripristino).
const ALLOWED = new Set(["keep", "discard", "trash", "review", "new"]);

export async function POST(req: Request) {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  if (!operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });

  const body = (await req.json().catch(() => ({}))) as { ids?: unknown; state?: unknown };
  const ids = Array.isArray(body.ids) ? body.ids.filter((n): n is number => Number.isInteger(n)) : [];
  const state = String(body.state ?? "");
  if (!ids.length) return NextResponse.json({ ok: false, message: "nessun messaggio selezionato" }, { status: 400 });
  if (!ALLOWED.has(state)) return NextResponse.json({ ok: false, message: `stato non ammesso: ${state}` }, { status: 400 });

  if (shouldUseMock()) {
    return NextResponse.json({ ok: true, simulated: true, count: ids.length, state, operator_uid: operatorUid });
  }
  try {
    // execute_kw: browse(ids).console_triage(state, operator_uid) → args = [ids, state, operatorUid]
    const res = await callKw("casafolino.mail.message", "console_triage", [ids, state, operatorUid]);
    return NextResponse.json(res as Record<string, unknown>);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
