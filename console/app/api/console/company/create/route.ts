// POST /api/console/company/create → crm.lead.console_create_company (azienda standalone, manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_create_company", req); }
