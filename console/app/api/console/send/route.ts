// POST /api/console/send → gateway Odoo console_send con attribution operatore (sessione).
import { forwardToGateway } from "@/lib/operatorSend";

export async function POST(req: Request) {
  return forwardToGateway("console_send", req);
}
