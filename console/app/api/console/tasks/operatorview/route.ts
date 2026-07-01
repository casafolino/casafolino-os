// POST /api/console/tasks/operatorview → cf.task.console_task_operator_view (gate + operator attribution server-side).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task", "console_task_operator_view", req);
}
