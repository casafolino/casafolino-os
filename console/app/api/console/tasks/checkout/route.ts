// POST /api/console/tasks/checkout → cf.task.console_task_checkout (gate + operator attribution server-side).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task", "console_task_checkout", req);
}
