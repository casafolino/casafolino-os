// POST /api/console/wizard/enrich-007 → crm.lead.console_enrich_007 (Serper+Groq, read-only, fail-soft).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_enrich_007", req); }
