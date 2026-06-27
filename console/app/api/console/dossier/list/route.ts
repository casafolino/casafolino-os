// POST /api/console/dossier/list — SOLO partner pinnati, raggruppati per cartella. Read-only gated.
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("res.partner", "console_dossier_list", req);
}
