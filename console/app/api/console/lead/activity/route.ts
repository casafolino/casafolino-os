import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → crm.lead.console_schedule_activity (mail.activity, user = operatore sessione).
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_schedule_activity", req); }
