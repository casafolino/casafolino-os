import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → crm.lead.console_lead_sla (semaforo reale da cf.task).
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_lead_sla", req); }
