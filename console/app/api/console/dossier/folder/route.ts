// POST /api/console/dossier/folder — crea o rinomina cartella. mode:"create"|"rename". Gated+audit.
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const method = body?.mode === "rename" ? "console_rename_folder" : "console_create_folder";
  // ricostruisco la req perché forwardOperatorCall rilegge il body
  const fwd = new Request(req.url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return forwardOperatorCall("res.partner", method, fwd);
}
