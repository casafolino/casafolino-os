import { forwardOperatorCall } from "@/lib/operatorSend";
// POST → res.partner.console_partner_dossier (header + 4 metric card + semaforo/tag).
export async function POST(req: Request) { return forwardOperatorCall("res.partner", "console_partner_dossier", req); }
