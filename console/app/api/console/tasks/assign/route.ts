// POST /api/console/tasks/assign → cf.task.console_task_assign (gate + operator attribution server-side).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task", "console_task_assign", req);
}
