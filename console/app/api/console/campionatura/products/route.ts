// POST /api/console/campionatura/products → cf.shipment.console_search_products (read-only).
// Catalogo vendibile per il picker. Nessun operator_uid: lettura gated _is_console nel gateway.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

export async function POST(req: Request) {
  const session = await auth();
  if (!session?.operatorUid) {
    return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  }
  const { query = "", limit = 20 } = (await req.json().catch(() => ({}))) as { query?: string; limit?: number };
  if (shouldUseMock()) {
    return NextResponse.json([
      { id: 1, name: "Crema di pistacchio 90g", code: "CFP-90", uom: "Unità" },
      { id: 2, name: "Pesto di pistacchio 180g", code: "PST-180", uom: "Unità" },
    ]);
  }
  try {
    const result = await callKw("cf.shipment", "console_search_products", [query, limit]);
    return NextResponse.json(result as unknown[]);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
