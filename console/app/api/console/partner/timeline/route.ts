import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → res.partner.console_partner_timeline (timeline unica cronologica, paginata).
export async function POST(req: Request) { return forwardOperatorCall("res.partner", "console_partner_timeline", req); }
