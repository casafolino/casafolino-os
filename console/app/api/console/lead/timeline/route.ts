// POST /api/console/lead/timeline → crm.lead.console_get_lead_timeline (operatore da sessione, audit).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("crm.lead", "console_get_lead_timeline", req);
}
