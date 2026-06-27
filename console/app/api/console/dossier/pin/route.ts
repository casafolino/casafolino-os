// POST /api/console/dossier/pin — toggle is_dossier (+ cartella) sul partner. Gated+audit.
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("res.partner", "console_toggle_dossier", req);
}
