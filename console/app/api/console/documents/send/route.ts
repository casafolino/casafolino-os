// POST /api/console/documents/send → res.partner.console_send_documents (libreria curata → outbound).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("res.partner", "console_send_documents", req); }
