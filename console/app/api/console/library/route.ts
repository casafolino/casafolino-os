// POST /api/console/library → casafolino.mail.message.console_library (materiali approvati, read-only).
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";
export async function POST() {
  const session = await auth();
  if (!session?.operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  if (shouldUseMock()) return NextResponse.json([{ id: 1, name: "Catalogo 2026", category: "catalogo", language: "it", fileName: "catalogo.pdf" }]);
  try { return NextResponse.json(await callKw("casafolino.mail.message", "console_library", [])); }
  catch (e) { return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 }); }
}
