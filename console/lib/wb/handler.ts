// Wrapper comune per gli handler /api/wb/*: applica la guardia scope server-side,
// gestisce errori e mock mode. L'handler concreto riceve lo scope risolto.
import { NextResponse } from "next/server";
import { guard, type Scope } from "@/lib/wb/scope";

type Producer = (ctx: { scope: Scope; req: Request }) => Promise<unknown>;

export function wbHandler(endpoint: string, produce: Producer) {
  return async function GET(req: Request) {
    const g = guard(req, endpoint);
    if (!g.ok) {
      return NextResponse.json({ ok: false, message: g.message }, { status: g.status });
    }
    try {
      const data = await produce({ scope: g.scope, req });
      return NextResponse.json({ ok: true, scope: g.scope, ...(data as object) });
    } catch (e) {
      return NextResponse.json(
        { ok: false, message: (e as Error).message ?? "errore wallboard" },
        { status: 500 },
      );
    }
  };
}

/** Inizio mese corrente in formato Odoo (YYYY-MM-DD). */
export function firstOfMonthISO(now = new Date()): string {
  const y = now.getUTCFullYear();
  const m = String(now.getUTCMonth() + 1).padStart(2, "0");
  return `${y}-${m}-01`;
}

/** Data odierna in formato Odoo (YYYY-MM-DD), UTC. */
export function todayISO(now = new Date()): string {
  return now.toISOString().slice(0, 10);
}
