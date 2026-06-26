// POST /api/console/catalog/init → casafolino.mail.message.console_catalog_init (precompila modale, read-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("casafolino.mail.message", "console_catalog_init", req); }
