// POST /api/console/lead/suggest → crm.lead.console_suggest_lead (titolo IA da mail, no-write).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_suggest_lead", req); }
