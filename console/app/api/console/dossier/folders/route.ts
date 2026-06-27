// POST /api/console/dossier/folders — lista cartelle + conteggi. Read-only gated.
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("res.partner", "console_dossier_folders", req);
}
