// POST /api/console/partner-bundle {partnerId} → bundle partner on-demand (lazy-load inbox).
// Sostituisce il prefetch di 12 bundle (Brief B perf): si carica solo alla selezione.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { getPartnerBundle } from "@/lib/bundle";

export async function POST(req: Request) {
  const session = await auth();
  if (!session?.operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  const { partnerId } = (await req.json().catch(() => ({}))) as { partnerId?: number };
  if (!partnerId) return NextResponse.json(null);
  const bundle = await getPartnerBundle(Number(partnerId));
  return NextResponse.json(bundle);
}
