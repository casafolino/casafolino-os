// POST /api/console/quicktask/commit → crm.lead.console_quicktask_commit (scrive dopo conferma card).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_quicktask_commit", req); }
