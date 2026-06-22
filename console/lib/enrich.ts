// Brief 8 — tipi + helper client per crea contatto/azienda da mail con IA + dedup.
// operator_uid sempre dalla sessione (manager-only nei gateway).
import { BP } from "@/lib/basePath";

export type Contatto = { nome: string; ruolo: string; email: string; telefono: string };
export type Azienda = { nome: string; dominio: string };
export type Indirizzo = { via: string; cap: string; citta: string; paese: string };
export type ProposedData = { contatto: Contatto; azienda: Azienda; indirizzo: Indirizzo };

export type DedupContact = { id: number; name: string; email: string; company: string; strength: string };
export type DedupCompany = { id: number; name: string; domain: string; strength: string };

export type EnrichResult = {
  mailId: number;
  hasBody: boolean;
  source: "signature" | "domain";
  proposed: ProposedData;
  dedupCandidates: { contacts: DedupContact[]; companies: DedupCompany[] };
  message?: string;
};

export type CreateResult = { ok?: boolean; linked?: boolean; partnerId?: number; name?: string; companyId?: number | false; message?: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BP}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return (await res.json()) as T;
}

export const enrichContact = (mailId: number) => post<EnrichResult>("/api/console/enrich/contact", { mailId });

export const createContact = (body: {
  data?: ProposedData;
  linkPartnerId?: number;
  linkCompanyId?: number;
  linkLeadId?: number;
  mailId?: number;
}) => post<CreateResult>("/api/console/contact/create", body);
