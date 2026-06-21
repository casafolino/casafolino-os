// POST /api/console/pipeline/board → crm.lead.console_pipeline_board (manager-only, operator da sessione).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("crm.lead", "console_pipeline_board", req);
}
