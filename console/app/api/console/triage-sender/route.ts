// POST /api/console/triage-sender { state, partnerId?|senderEmail?, view, scopeAll? }
// Nuke-all per mittente SERVER-SIDE: prende TUTTI gli id di quel mittente entro scope+vista,
// poi console_triage in bulk. operator_uid dalla sessione (scope non bypassabile dal client).
// Ritorna count + ids + prev (stato precedente) per l'undo dell'intero set. Mai unlink.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";
import { fetchSenderIds, type InboxViewKind } from "@/lib/bundle";

const ALLOWED = new Set(["keep", "discard", "trash", "review", "new"]);
const VIEWS = new Set(["queue", "all", "keep", "discard", "trash"]);

export async function POST(req: Request) {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  if (!operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });

  const body = (await req.json().catch(() => ({}))) as {
    state?: unknown; partnerId?: unknown; senderEmail?: unknown; view?: unknown; scopeAll?: unknown;
  };
  const state = String(body.state ?? "");
  if (!ALLOWED.has(state)) return NextResponse.json({ ok: false, message: `stato non ammesso: ${state}` }, { status: 400 });
  const view = (VIEWS.has(String(body.view)) ? String(body.view) : "queue") as InboxViewKind;
  const partnerId = Number.isInteger(body.partnerId) ? (body.partnerId as number) : undefined;
  const senderEmail = typeof body.senderEmail === "string" ? body.senderEmail : undefined;
  const scopeAll = body.scopeAll === true;
  if (!partnerId && !senderEmail) return NextResponse.json({ ok: false, message: "mittente mancante" }, { status: 400 });

  if (shouldUseMock()) return NextResponse.json({ ok: true, simulated: true, count: 0, ids: [], prev: {}, state });

  try {
    // scope SEMPRE da operator_uid (sessione); scopeAll = solo toggle SOFT consentito.
    const rows = await fetchSenderIds({ operatorUid, scopeAll }, { partnerId, senderEmail, view });
    const ids = rows.map((r) => r.id);
    if (!ids.length) return NextResponse.json({ ok: true, count: 0, ids: [], prev: {}, state });
    const prev: Record<number, string> = {};
    rows.forEach((r) => { prev[r.id] = r.state; });
    await callKw("casafolino.mail.message", "console_triage", [ids, state, operatorUid]);
    return NextResponse.json({ ok: true, count: ids.length, ids, prev, state });
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
