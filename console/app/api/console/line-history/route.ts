// POST /api/console/line-history {partner_id, category_id} — lente: storia linea (ordini/preventivi/campionature). Read-only gated.
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("res.partner", "console_line_history", req);
}
