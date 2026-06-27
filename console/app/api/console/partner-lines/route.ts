// POST /api/console/partner-lines {partner_id} — lente: linee di prodotto del cliente + conteggi. Read-only gated.
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("res.partner", "console_partner_lines", req);
}
