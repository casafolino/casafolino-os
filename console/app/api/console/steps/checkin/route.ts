// POST /api/console/steps/checkin → cf.task.step.console_step_checkin (ownership server-side).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task.step", "console_step_checkin", req);
}
