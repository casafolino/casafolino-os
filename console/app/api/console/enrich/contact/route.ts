// POST /api/console/enrich/contact → res.partner.console_enrich_contact (manager-only, no-write).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("res.partner", "console_enrich_contact", req);
}
