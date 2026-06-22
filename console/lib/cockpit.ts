// Brief 15 — tipi + helper client per il cruscotto mail. operator_uid dalla sessione (manager-only).
import { BP } from "@/lib/basePath";

export type Resolved = { exists: boolean; id: number | false; name: string };
export type CockpitData = {
  mailId: number;
  sender: { email: string; name: string };
  partner: Resolved & { isCompany?: boolean };
  company: Resolved;
  lead: Resolved & { stage?: string; stageId?: number | false };
  dossier: Resolved;
  leadStages: { id: number; name: string }[];
  message?: string;
};

export type CreateCompanyResult = { ok?: boolean; partnerId?: number; name?: string; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const getMailCockpit = (mailId: number) => post<CockpitData>("/api/console/mail/cockpit", { mailId });
export const createCompany = (body: { data: { nome: string; dominio?: string; citta?: string }; mailId?: number }) =>
  post<CreateCompanyResult>("/api/console/company/create", body);
