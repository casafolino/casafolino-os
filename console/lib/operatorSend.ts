// Inoltro send/reply al gateway Odoo con attribution operatore (Phase 2 S5).
// ANTI-SPOOF: operator_uid è SEMPRE preso dalla sessione server-side (auth()) e
// l'eventuale operator_uid nel body del client viene scartato. Il client non può
// fornirlo né sovrascriverlo. I dati passano via console_api (callKw), invariato.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

type GatewayMethod = "console_send" | "console_reply";

export async function forwardToGateway(method: GatewayMethod, req: Request): Promise<NextResponse> {
  const session = await auth();
  const operatorUid = session?.operatorUid;
  if (!operatorUid) {
    return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  }

  const raw = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  // Scarta qualsiasi operator_uid arrivato dal client, poi inietta quello della sessione.
  const { operator_uid: _ignored, ...clean } = raw;
  const payload = { ...clean, operator_uid: operatorUid };

  if (shouldUseMock()) {
    return NextResponse.json({
      ok: true,
      simulated: true,
      method,
      operator_uid: operatorUid,
      message: `${method} simulato (mock) — operatore ${operatorUid}`,
    });
  }

  try {
    const result = await callKw("casafolino.mail.message", method, [payload]);
    return NextResponse.json(result as Record<string, unknown>);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
