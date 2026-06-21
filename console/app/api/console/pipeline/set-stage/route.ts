// POST /api/console/pipeline/set-stage → crm.lead.console_set_lead_stage (manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("crm.lead", "console_set_lead_stage", req);
}
