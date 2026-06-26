// POST /api/console/catalog/send → casafolino.mail.message.console_send_catalog (invio via ir.mail_server).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("casafolino.mail.message", "console_send_catalog", req); }
