// POST /api/console/steps/remind → cf.task.step.console_step_remind (sollecito da timeline rossa).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task.step", "console_step_remind", req);
}
