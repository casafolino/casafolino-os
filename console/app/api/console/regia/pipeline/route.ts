import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → crm.lead.console_regia_pipeline (lista piatta ordinata semaforo).
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_regia_pipeline", req); }
