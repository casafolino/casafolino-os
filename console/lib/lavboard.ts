// Tipi + client helpers per la board Lavorazioni (task cf.task, lifecycle BackOperation).
// operator_uid NON è mai passato dal client: lo inietta il route server-side (forwardOperatorCall).
import { BP } from "@/lib/basePath";

export type TaskCard = {
  id: number;
  name: string;
  state: string;
  isPool: boolean;
  titolareId: number | false;
  titolareName: string | false;
  assegnataDa: string | false;
  deadline: string | false;
  priority: string;
  checkinAt: string | false;
  checkoutAt: string | false;
  firmata: boolean;
};

export type TaskColumn = {
  key: string;
  kind: "pool" | "assignee";
  name: string;
  employeeId: number | false;
  count: number;
  cards: TaskCard[];
};

export type TaskBoard = { ok?: boolean; columns: TaskColumn[]; message?: string };
export type OperatorView = {
  ok?: boolean;
  employeeId: number | false;
  pool: TaskCard[];
  mine: TaskCard[];
  message?: string;
};
export type TaskActionResult = Partial<TaskCard> & { ok?: boolean; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const getTaskBoard = () => post<TaskBoard>("/api/console/tasks/board", {});
export const getOperatorTasks = () => post<OperatorView>("/api/console/tasks/operatorview", {});
export const claimTask = (taskId: number) => post<TaskActionResult>("/api/console/tasks/claim", { taskId });
export const taskCheckin = (taskId: number) => post<TaskActionResult>("/api/console/tasks/checkin", { taskId });
export const taskCheckout = (taskId: number) => post<TaskActionResult>("/api/console/tasks/checkout", { taskId });
export const taskSign = (taskId: number, firma?: string) =>
  post<TaskActionResult>("/api/console/tasks/sign", { taskId, firma });
export const assignTask = (taskId: number, assigneeEmployeeId: number | null) =>
  post<TaskActionResult>("/api/console/tasks/assign", { taskId, assignee_employee_id: assigneeEmployeeId });

export const TASK_STATE_LABEL: Record<string, string> = {
  bozza: "Da fare",
  in_corso: "In corso",
  taken: "Preso",
  blocked: "Bloccato",
  chiuso: "Chiuso",
  annullato: "Annullato",
};

// Colonna → colore accento (riusa le var --op-* del tema). Pool = neutro.
export function columnAccent(col: TaskColumn): string {
  if (col.kind === "pool") return "var(--op-other)";
  const palette = ["var(--op-antonio)", "var(--op-josefina)", "var(--op-martina)", "var(--accent)"];
  const idx = typeof col.employeeId === "number" ? col.employeeId % palette.length : 0;
  return palette[idx];
}

// Qual è la prossima azione lifecycle per una card "mia"/assegnata.
export type NextAction = "checkin" | "checkout" | "sign" | null;
export function nextAction(card: TaskCard): NextAction {
  if (card.state === "chiuso" || card.state === "annullato") return null;
  if (card.state === "in_corso") return card.checkoutAt ? "sign" : "checkout";
  // bozza/taken con titolare = claimata, non ancora avviata
  if (card.titolareId) return "checkin";
  return null;
}
