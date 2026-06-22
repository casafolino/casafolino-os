// POST /api/console/partner/sync-mail → res.partner.console_sync_partner_mail (recupero mail pre-cutoff, manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("res.partner", "console_sync_partner_mail", req); }
