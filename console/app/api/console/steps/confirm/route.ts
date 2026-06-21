// POST /api/console/steps/confirm → cf.task.step.console_step_confirm.
// Logistica: trackingCode+carrier nel body → scritti sulla spedizione prima del confirm;
// se mancano il gateway solleva errore (gestito a UI).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task.step", "console_step_confirm", req);
}
