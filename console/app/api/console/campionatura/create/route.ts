// POST /api/console/campionatura/create → cf.shipment.console_crea_campionatura.
// originatore = operatore della sessione (anti-spoof: operator_uid dal JWT, non dal body).
import { forwardOperatorCall } from "@/lib/operatorSend";

export async function POST(req: Request) {
  return forwardOperatorCall("cf.shipment", "console_crea_campionatura", req);
}
