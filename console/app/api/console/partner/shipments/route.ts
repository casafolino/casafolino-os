import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → res.partner.console_partner_shipments (cf.shipment campionature, sudo gateway).
export async function POST(req: Request) { return forwardOperatorCall("res.partner", "console_partner_shipments", req); }
