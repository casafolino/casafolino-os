// POST /api/console/campionatura/timeline → cf.shipment.console_get_campionatura_timeline.
// Read-only: step task (ruolo/stato/semaforo) + spedizione (stato/tracking).
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

export async function POST(req: Request) {
  const session = await auth();
  if (!session?.operatorUid) {
    return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  }
  const { shipmentId } = (await req.json().catch(() => ({}))) as { shipmentId?: number };
  if (!shipmentId) {
    return NextResponse.json({ ok: false, message: "shipmentId mancante" }, { status: 400 });
  }
  if (shouldUseMock()) {
    return NextResponse.json({
      shipmentId, name: "SMP/0001", partner: "Cliente Demo", shipmentState: "preparazione",
      carrier: "", tracking: "", sampleCode: "CAMP/0001", taskTrafficLight: "green",
      steps: [
        { stepId: 1, role: "coordinazione", assignee: "Maria Mirabelli", state: "confermato", trafficLight: "green", hours: 0.4 },
        { stepId: 2, role: "creazione", assignee: "Anna Macri", state: "in_corso", trafficLight: "yellow", hours: 5 },
        { stepId: 3, role: "logistica", assignee: "Teresa", state: "da_fare", trafficLight: "green", hours: 0 },
      ],
    });
  }
  try {
    const result = await callKw("cf.shipment", "console_get_campionatura_timeline", [shipmentId]);
    return NextResponse.json(result as Record<string, unknown>);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
