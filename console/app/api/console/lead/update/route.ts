// POST /api/console/lead/update → crm.lead.console_update_lead (whitelist campi, manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_update_lead", req); }
