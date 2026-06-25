// Fase 2 — Quick-Task NL: parse (read-only) + commit (scrive dopo conferma card). operator_uid dalla sessione.
import { BP } from "@/lib/basePath";

export type AssigneeResolved = { name: string; userId: number | null; employeeId: number | null };
export type ActionType = "catalogo" | "email" | "follow-up" | "sollecito" | "campione" | "task" | "";

export type ParsedQuicktask = {
  ok?: boolean;
  text: string;
  assignee: { raw: string; resolved: AssigneeResolved | null };
  actionType: ActionType;
  objectRef: string;
  dueDate: string;
  quantity: number | null;
  needsReview: boolean;
  message?: string;
};

export type CommitResult = {
  ok?: boolean;
  kind?: "activity" | "campionatura" | "task";
  id?: number;
  assigneeUid?: number;
  resModel?: string;
  resId?: number;
  name?: string;
  shipment_id?: number;
  message?: string;
};

export type CommitPayload = {
  action_type: ActionType;
  assignee_user_id?: number | null;
  assignee_employee_id?: number | null;
  partner_id?: number | null;
  lead_id?: number | null;
  summary?: string;
  due_date?: string;
  lines?: { productId: number; qty: number }[];
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const parseQuicktask = (text: string) =>
  post<ParsedQuicktask>("/api/console/quicktask/parse", { text });

export const commitQuicktask = (body: CommitPayload) =>
  post<CommitResult>("/api/console/quicktask/commit", body);
