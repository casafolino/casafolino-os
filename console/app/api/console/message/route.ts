// GET /api/console/message?id=N → corpo completo (body_html) di un messaggio.
// Read-only via console_api (ACL read su casafolino.mail.message). Auth-gated.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { shouldUseMock, callKw } from "@/lib/odoo";

export async function GET(req: Request) {
  const session = await auth();
  if (!session?.operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
  const id = Number(new URL(req.url).searchParams.get("id"));
  if (!Number.isInteger(id) || id <= 0) return NextResponse.json({ ok: false, message: "id non valido" }, { status: 400 });

  if (shouldUseMock()) {
    return NextResponse.json({ ok: true, id, subject: "(mock)", senderName: "Mock", senderEmail: "mock@x.it", date: "", bodyHtml: "<p>Corpo mail (mock).</p>",
      attachments: [{ id: 1, message_id: id, name: "preventivo.pdf", size: 84213, mimetype: "application/pdf" }] });
  }
  try {
    const rows = await callKw<Record<string, unknown>[]>("casafolino.mail.message", "read",
      [[id], ["subject", "sender_email", "sender_name", "email_date", "body_html", "snippet", "account_id"]]);
    const r = rows?.[0];
    if (!r) return NextResponse.json({ ok: false, message: "non trovato" }, { status: 404 });
    const bodyHtml = (r.body_html as string) || (r.snippet ? `<p>${r.snippet}</p>` : "<p class='muted'>(nessun corpo)</p>");
    // allegati (gated, read-only). Best-effort: un errore qui non rompe il corpo.
    let attachments: unknown[] = [];
    try {
      const attRes = await callKw<{ attachments?: unknown[] }>("casafolino.mail.message", "console_mail_attachments", [[id], session.operatorUid]);
      attachments = attRes?.attachments ?? [];
    } catch { attachments = []; }
    return NextResponse.json({
      ok: true, id,
      subject: r.subject ?? "", senderName: r.sender_name ?? "", senderEmail: r.sender_email ?? "",
      date: r.email_date ?? "", bodyHtml, attachments,
    });
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
