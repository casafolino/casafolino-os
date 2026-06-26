// POST /api/console/quicktask/parse → crm.lead.console_parse_quicktask (parsing NL, NESSUNA scrittura).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_parse_quicktask", req); }
