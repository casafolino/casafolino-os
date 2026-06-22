// POST /api/console/ricetta/create → res.partner.console_crea_ricetta (cf.task R&D, manager-only).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("res.partner", "console_crea_ricetta", req); }
