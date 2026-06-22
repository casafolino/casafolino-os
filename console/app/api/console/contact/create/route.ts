// POST /api/console/contact/create → res.partner.console_create_contact (manager-only, scrive dati revisionati).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("res.partner", "console_create_contact", req);
}
