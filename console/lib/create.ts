// Brief 9 — tipi + helper client per crea lead / crea dossier. operator_uid dalla sessione (manager-only).
import { BP } from "@/lib/basePath";

export type LeadSuggest = { title: string; emailFrom: string; partnerId: number | null; aiUsed: boolean; message?: string };
export type CreateLeadResult = { ok?: boolean; leadId?: number; name?: string; stageId?: number; stageName?: string; message?: string };
export type CreateDossierResult = { ok?: boolean; dossierId?: number; name?: string; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const suggestLead = (mailId: number) => post<LeadSuggest>("/api/console/lead/suggest", { mailId });

export const createLeadRich = (body: {
  data: { name: string; emailFrom?: string };
  partnerId?: number;
  stageId?: number;
  fromMailId?: number;
}) => post<CreateLeadResult>("/api/console/lead/create", body);

export const createDossier = (body: {
  data: { name: string };
  partnerId?: number;
  leadId?: number;
}) => post<CreateDossierResult>("/api/console/dossier/create", body);
