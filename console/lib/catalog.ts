// Fase 2 WI-A — Step 4 "Invia catalogo": init (precompila modale) + send (via ir.mail_server).
import { BP } from "@/lib/basePath";

export type CatalogAccount = { id: number; name: string; email: string };
export type CatalogMaterial = { id: number; name: string; fileName: string; language: string };

export type CatalogInit = {
  ok?: boolean;
  language: string;
  to: string;
  toName: string;
  accounts: CatalogAccount[];
  subject: string;
  body: string;
  material: CatalogMaterial | null;
  hasAttachment: boolean;
  warn: string | null;
  languages: string[];
  message?: string;
};

export type CatalogSendResult = {
  ok?: boolean;
  phase?: string;
  state?: string;
  attachmentSent?: boolean;
  catalogLanguage?: string;
  to?: string;
  draft_id?: number;
  outbox_id?: number;
  blocked?: string;
  message?: string;
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const catalogInit = (body: { partnerId?: number; leadId?: number; language?: string }) =>
  post<CatalogInit>("/api/console/catalog/init", body);

export const sendCatalog = (body: {
  partnerId?: number; leadId?: number; accountId: number; language: string; subject: string; body: string;
}) => post<CatalogSendResult>("/api/console/catalog/send", body);
