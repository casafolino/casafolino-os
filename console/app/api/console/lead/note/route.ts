import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → crm.lead.console_post_note (nota nativa, author = operatore sessione, sudo gateway).
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_post_note", req); }
