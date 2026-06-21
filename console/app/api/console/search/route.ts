// POST /api/console/search → crm.lead.console_universal_search (manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("crm.lead", "console_universal_search", req);
}
