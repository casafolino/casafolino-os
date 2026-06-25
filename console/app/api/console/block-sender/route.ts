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
    mode?: unknown; messageId?: unknown; messageIds?: unknown; scope?: unknown; patterns?: unknown;
  };
  const mode = String(body.mode ?? "block");
  const scope = SCOPES.has(String(body.scope)) ? String(body.scope) : "domain";

  // Anteprima massa: domini distinti dalla selezione + conteggi (per il dialog checkbox).
  if (mode === "preview") {
    const ids = Array.isArray(body.messageIds) ? body.messageIds.filter((n): n is number => Number.isInteger(n)) : [];
    if (!ids.length) return NextResponse.json({ ok: false, message: "nessun messaggio selezionato" }, { status: 400 });
    if (shouldUseMock()) {
      return NextResponse.json({ ok: true, groups: [
        { pattern_type: "domain", pattern_value: "temu.com", is_free_domain: false, queue_count: 3, selected_count: 2 },
        { pattern_type: "email_exact", pattern_value: "x@gmail.com", is_free_domain: true, queue_count: 1, selected_count: 1 },
      ] });
    }
    try {
      const res = await callKw("casafolino.mail.message", "console_block_sender_preview", [ids, operatorUid]);
      return NextResponse.json(res as Record<string, unknown>);
    } catch (e) {
      return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
    }
  }

  // Esecuzione massa: SOLO i pattern confermati (domini despuntati esclusi a monte).
  if (mode === "block-patterns") {
    const raw = Array.isArray(body.patterns) ? body.patterns : [];
    const patterns = raw
      .map((p) => p as { pattern_type?: unknown; pattern_value?: unknown })
      .filter((p) => typeof p.pattern_value === "string" && (p.pattern_value as string).trim())
      .map((p) => ({ pattern_type: p.pattern_type === "email_exact" ? "email_exact" : "domain", pattern_value: (p.pattern_value as string).trim().toLowerCase() }));
    if (!patterns.length) return NextResponse.json({ ok: false, message: "nessun dominio confermato" }, { status: 400 });
    if (shouldUseMock()) return NextResponse.json({ ok: true, simulated: true, retro_total: 0, results: [] });
    try {
      const res = await callKw("casafolino.mail.message", "console_block_patterns", [patterns, operatorUid]);
      return NextResponse.json(res as Record<string, unknown>);
    } catch (e) {
      return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
    }
  }

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
