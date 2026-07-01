// POST /api/console/tasks/sign → cf.task.console_task_sign (gate + operator attribution server-side).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task", "console_task_sign", req);
}
