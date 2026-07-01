import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → crm.lead.console_regia_kpis (4 KPI Regia, read-only gated).
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_regia_kpis", req); }
