// POST /api/console/mail/cockpit → crm.lead.console_mail_cockpit (resolver mittente, manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_mail_cockpit", req); }
