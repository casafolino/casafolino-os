// GET /api/console/attachment?id=N → download proxy di UN allegato mail.
// Il blob arriva gated dal backend (console_attachment_blob, solo allegati di casafolino.mail.message).
// Auth-gated; nessuna lettura arbitraria di ir.attachment dal client.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

export async function GET(req: Request) {
  const session = await auth();
  if (!session?.operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  const id = Number(new URL(req.url).searchParams.get("id"));
  if (!Number.isInteger(id) || id <= 0) return NextResponse.json({ ok: false, message: "id non valido" }, { status: 400 });

  if (shouldUseMock()) return new NextResponse("mock", { headers: { "Content-Type": "text/plain" } });

  try {
    const res = await callKw<{ ok?: boolean; name?: string; mimetype?: string; datas?: string; message?: string }>(
      "casafolino.mail.message", "console_attachment_blob", [id, session.operatorUid]);
    if (!res?.ok || !res.datas) {
      return NextResponse.json({ ok: false, message: res?.message ?? "allegato non disponibile" }, { status: 404 });
    }
    const buf = Buffer.from(res.datas, "base64");
    const name = (res.name ?? "file").replace(/[\r\n"]/g, "");
    return new NextResponse(buf, {
      headers: {
        "Content-Type": res.mimetype || "application/octet-stream",
        "Content-Disposition": `attachment; filename="${name}"`,
        "Content-Length": String(buf.length),
        "Cache-Control": "private, no-store",
      },
    });
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
