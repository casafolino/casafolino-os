// POST /api/console/read { ids:number[], isRead:boolean } → gateway console_mark_read.
// operator_uid dalla sessione (anti-spoof). Solo is_read via gateway sudo+audit.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

export async function POST(req: Request) {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  if (!operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });

  const body = (await req.json().catch(() => ({}))) as { ids?: unknown; isRead?: unknown };
  const ids = Array.isArray(body.ids) ? body.ids.filter((n): n is number => Number.isInteger(n)) : [];
  const isRead = body.isRead !== false; // default true
  if (!ids.length) return NextResponse.json({ ok: false, message: "nessun messaggio" }, { status: 400 });

  if (shouldUseMock()) return NextResponse.json({ ok: true, simulated: true, count: ids.length, is_read: isRead });
  try {
    const res = await callKw("casafolino.mail.message", "console_mark_read", [ids, isRead, operatorUid]);
    return NextResponse.json(res as Record<string, unknown>);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
