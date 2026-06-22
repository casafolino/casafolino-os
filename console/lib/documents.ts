// Brief 10 — tipi + helper client per Invia documenti (libreria curata) + Ricetta (cf.task R&D).
import { BP } from "@/lib/basePath";

export type LibraryDoc = { id: number; name: string; category: string; language: string; fileName: string };
export type SendDocsResult = { ok?: boolean; state?: string; phase?: string; to?: string; message?: string };
export type RicettaStep = { stepId: number; role: string; name: string; assignee: string; state: string; trafficLight: string };
export type RicettaResult = { ok?: boolean; taskId?: number; name?: string; taskState?: string; trafficLight?: string; steps?: RicettaStep[]; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const getLibrary = () => post<LibraryDoc[]>("/api/console/library", {});

export const sendDocuments = (body: {
  leadId?: number; partnerId?: number; materialIds: number[]; subject?: string; body?: string;
}) => post<SendDocsResult>("/api/console/documents/send", body);

export const creaRicetta = (body: {
  leadId?: number; partnerId?: number; recipeSpec: string; productType?: string; assignees?: Record<string, number>;
}) => post<RicettaResult>("/api/console/ricetta/create", body);
