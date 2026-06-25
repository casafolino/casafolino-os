// POST /api/console/wizard/vat-lookup → crm.lead.console_vat_lookup (dedup + VIES, read-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_vat_lookup", req); }
