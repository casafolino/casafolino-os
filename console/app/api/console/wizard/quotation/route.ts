// POST /api/console/wizard/quotation → sale.order.console_create_quotation (bozza, mai confermata).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) { return forwardOperatorCall("sale.order", "console_create_quotation", req); }
