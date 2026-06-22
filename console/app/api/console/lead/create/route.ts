// POST /api/console/lead/create → crm.lead.console_create_lead (manager-only, owner=operatore).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_create_lead", req); }
