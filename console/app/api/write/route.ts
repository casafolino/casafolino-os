// POST /api/write { action, payload } → scritture via Odoo (server). Mai SMTP raw.
import { NextResponse } from "next/server";
import { createLead, linkMessageToLead, sendMail } from "@/lib/writes";

export async function POST(req: Request) {
  try {
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
      default:
        return NextResponse.json({ ok: false, message: `azione sconosciuta: ${action}` }, { status: 400 });
    }
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ ok: false, message: (e as Error).message }, { status: 500 });
  }
}
