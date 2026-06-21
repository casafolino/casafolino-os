// POST /api/console/steps/list → cf.task.step.console_list_my_steps (operatore da sessione).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task.step", "console_list_my_steps", req);
}
