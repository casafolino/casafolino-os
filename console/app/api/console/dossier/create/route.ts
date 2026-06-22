// POST /api/console/dossier/create → crm.lead.console_create_dossier (project.project sudo, manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("crm.lead", "console_create_dossier", req); }
