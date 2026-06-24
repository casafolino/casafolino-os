import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → res.partner.console_partner_orders (tutti i sale.order, sudo gateway).
export async function POST(req: Request) { return forwardOperatorCall("res.partner", "console_partner_orders", req); }
