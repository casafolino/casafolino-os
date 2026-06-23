// POST /api/write { action, payload } → scritture via Odoo (server). Mai SMTP raw.
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { createLead, linkMessageToLead, sendMail, postLeadNote, createLeadActivity } from "@/lib/writes";

export async function POST(req: Request) {
  try {
    const session = await auth();
    if (!session?.operatorUid) return NextResponse.json({ ok: false, message: "unauthorized" }, { status: 401 });
    const { action, payload } = (await req.json()) as { action: string; payload: Record<string, unknown> };
    let result;
    switch (action) {
      case "createLead":
        result = await createLead(payload as { partnerId?: number | null; name: string; emailFrom?: string });
        break;
      case "linkMessageToLead":
        result = await linkMessageToLead(payload as { messageId: number; leadId: number });
        break;
      case "sendMail":
        result = await sendMail(payload as { to: string; subject: string; bodyHtml: string });
        break;
      case "postLeadNote":
        // operatorUid dalla sessione (non dal client): autore/attribution affidabili.
        result = await postLeadNote({ ...(payload as { leadId: number; body: string }), operatorUid: session.operatorUid });
        break;
      case "createLeadActivity":
        result = await createLeadActivity({ ...(payload as { leadId: number; summary: string; dueDate: string }), operatorUid: session.operatorUid });
        break;
      default:
        return NextResponse.json({ ok: false, message: `azione sconosciuta: ${action}` }, { status: 400 });
    }
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
