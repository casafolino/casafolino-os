// POST /api/console/block-sender
//  mode:"info"  { messageId }                  → console_block_sender_info (dialog di conferma)
//  mode:"block" { messageIds[], scope }        → console_block_sender (policy auto_discard + sweep)
// operator_uid PRESO DALLA SESSIONE (anti-spoof: il body non può fornirlo).
// Gateway audited su casafolino.mail.message; mai write raw, mai unlink.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

const SCOPES = new Set(["domain", "email_exact"]);

export async function POST(req: Request) {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  if (!operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });

  const body = (await req.json().catch(() => ({}))) as {
    mode?: unknown; messageId?: unknown; messageIds?: unknown; scope?: unknown;
  };
  const mode = String(body.mode ?? "block");
  const scope = SCOPES.has(String(body.scope)) ? String(body.scope) : "domain";

  if (mode === "info") {
    const id = Number.isInteger(body.messageId) ? (body.messageId as number) : 0;
    if (!id) return NextResponse.json({ ok: false, message: "messaggio mancante" }, { status: 400 });
    if (shouldUseMock()) {
      return NextResponse.json({ ok: true, sender_email: "demo@temu.com", domain: "temu.com", is_free_domain: false, queue_count_domain: 3, queue_count_email: 1 });
    }
    try {
      const res = await callKw("casafolino.mail.message", "console_block_sender_info", [[id], operatorUid]);
      return NextResponse.json(res as Record<string, unknown>);
    } catch (e) {
      return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
    }
  }

  const ids = Array.isArray(body.messageIds) ? body.messageIds.filter((n): n is number => Number.isInteger(n)) : [];
  if (!ids.length) return NextResponse.json({ ok: false, message: "nessun messaggio selezionato" }, { status: 400 });
  if (shouldUseMock()) {
    return NextResponse.json({ ok: true, simulated: true, retro_total: 0, results: [] });
  }
  try {
    const res = await callKw("casafolino.mail.message", "console_block_sender", [ids, scope, operatorUid]);
    return NextResponse.json(res as Record<string, unknown>);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
