// POST /api/console/campionatura/defaults → assegnatari default + operatori (read-only).
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

export async function POST() {
  const session = await auth();
  if (!session?.operatorUid) {
    return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  }
  if (shouldUseMock()) {
    return NextResponse.json({
      defaults: {
        coordinazione: { uid: 9, name: "Maria Mirabelli" },
        creazione: { uid: 22, name: "Anna Macri" },
        logistica: { uid: 11, name: "Teresa" },
      },
      operators: [
        { uid: 9, name: "Maria Mirabelli" }, { uid: 22, name: "Anna Macri" },
        { uid: 11, name: "Teresa" }, { uid: 23, name: "Valentina Gamberale" },
      ],
    });
  }
  try {
    const result = await callKw("cf.shipment", "console_campionatura_defaults", []);
    return NextResponse.json(result as Record<string, unknown>);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
