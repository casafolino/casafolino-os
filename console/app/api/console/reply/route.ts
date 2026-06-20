// POST /api/console/reply → gateway Odoo console_reply con attribution operatore (sessione).
import { forwardToGateway } from "@/lib/operatorSend";

export async function POST(req: Request) {
  return forwardToGateway("console_reply", req);
}
