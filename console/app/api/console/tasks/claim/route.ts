// POST /api/console/tasks/claim → cf.task.console_task_claim (gate + operator attribution server-side).
import { forwardOperatorCall } from "@/lib/operatorSend";
export async function POST(req: Request) {
  return forwardOperatorCall("cf.task", "console_task_claim", req);
}
