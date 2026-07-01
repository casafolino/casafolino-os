// POST /api/console/tasks/checkin → cf.task.console_task_checkin (gate + operator attribution server-side).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task", "console_task_checkin", req);
}
