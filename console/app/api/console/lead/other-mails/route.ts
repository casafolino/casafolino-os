// POST /api/console/lead/other-mails → crm.lead.console_get_lead_other_mails (operatore da sessione, audit).
// S1 — mail del partner non assegnate a questa trattativa (lead_id vuoto).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("crm.lead", "console_get_lead_other_mails", req);
}
