// POST /api/console/lead/get → crm.lead.console_get_lead (operatore da sessione, audit).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("crm.lead", "console_get_lead", req);
}
