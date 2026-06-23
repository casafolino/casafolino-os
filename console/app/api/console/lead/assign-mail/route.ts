// POST /api/console/lead/assign-mail → crm.lead.console_assign_mail_to_lead (operatore da sessione, audit).
// S1 — assegna una mail (e le sorelle del thread) a questa trattativa scrivendo lead_id.
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("crm.lead", "console_assign_mail_to_lead", req);
}
